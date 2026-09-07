using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using Microsoft.JSInterop;

namespace gRisk.Web.Services;

public sealed record AuthUser(string Id, string? Email, string? Name, IReadOnlyList<string> Roles, bool IsSuperuser);

public sealed class AuthService(HttpClient httpClient, IJSRuntime jsRuntime)
{
    private const string StorageKey = "grisk.access_token";
    private string? _accessToken;

    public event Action? SessionChanged;

    public bool IsAuthenticated => CurrentUser is not null;
    public AuthUser? CurrentUser { get; private set; }

    public async Task InitializeAsync()
    {
        if (_accessToken is not null)
        {
            return;
        }

        _accessToken = await jsRuntime.InvokeAsync<string?>("sessionStorage.getItem", StorageKey);
        CurrentUser = ParseUser(_accessToken);
        if (_accessToken is not null && CurrentUser is null)
        {
            await LogoutAsync();
        }
    }

    public async Task<(bool Success, string? Error)> LoginAsync(string email, string password)
    {
        using var content = new FormUrlEncodedContent(new Dictionary<string, string>
        {
            ["username"] = email.Trim(),
            ["password"] = password,
        });

        using var response = await httpClient.PostAsync("api/v1/auth/login", content);
        if (!response.IsSuccessStatusCode)
        {
            return (false, "The email address or password is incorrect.");
        }

        var token = await response.Content.ReadFromJsonAsync<TokenResponse>();
        if (string.IsNullOrWhiteSpace(token?.AccessToken))
        {
            return (false, "The server did not return a valid access token.");
        }

        var user = ParseUser(token.AccessToken);
        if (user is null)
        {
            return (false, "The access token returned by the server is invalid.");
        }

        _accessToken = token.AccessToken;
        CurrentUser = user;
        await jsRuntime.InvokeVoidAsync("sessionStorage.setItem", StorageKey, _accessToken);
        SessionChanged?.Invoke();
        return (true, null);
    }

    public async Task LogoutAsync()
    {
        _accessToken = null;
        CurrentUser = null;
        await jsRuntime.InvokeVoidAsync("sessionStorage.removeItem", StorageKey);
        SessionChanged?.Invoke();
    }

    public async Task<string?> GetAccessTokenAsync()
    {
        await InitializeAsync();
        return _accessToken;
    }

    private static AuthUser? ParseUser(string? token)
    {
        if (string.IsNullOrWhiteSpace(token))
        {
            return null;
        }

        try
        {
            var segments = token.Split('.');
            if (segments.Length != 3)
            {
                return null;
            }

            var payload = segments[1].Replace('-', '+').Replace('_', '/');
            payload = payload.PadRight(payload.Length + ((4 - payload.Length % 4) % 4), '=');
            var json = Encoding.UTF8.GetString(Convert.FromBase64String(payload));
            using var document = JsonDocument.Parse(json);
            var root = document.RootElement;

            if (!root.TryGetProperty("sub", out var subject) || string.IsNullOrWhiteSpace(subject.GetString()))
            {
                return null;
            }

            if (root.TryGetProperty("exp", out var expiry) && expiry.TryGetInt64(out var expirySeconds))
            {
                if (DateTimeOffset.FromUnixTimeSeconds(expirySeconds) <= DateTimeOffset.UtcNow)
                {
                    return null;
                }
            }

            var roles = new List<string>();
            if (root.TryGetProperty("roles", out var rolesElement) && rolesElement.ValueKind == JsonValueKind.Array)
            {
                roles.AddRange(
                    rolesElement.EnumerateArray()
                        .Select(item => item.GetString())
                        .Where(item => !string.IsNullOrWhiteSpace(item))
                        .Select(item => item!));
            }

            return new AuthUser(
                subject.GetString()!,
                root.TryGetProperty("email", out var email) ? email.GetString() : null,
                root.TryGetProperty("name", out var name) ? name.GetString() : null,
                roles,
                root.TryGetProperty("is_superuser", out var superuser) && superuser.ValueKind == JsonValueKind.True);
        }
        catch (FormatException)
        {
            return null;
        }
        catch (JsonException)
        {
            return null;
        }
    }

    private sealed class TokenResponse
    {
        public string AccessToken { get; set; } = string.Empty;
    }
}
