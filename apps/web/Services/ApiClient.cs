using System.Net.Http.Headers;
using System.Net.Http.Json;

namespace gRisk.Web.Services;

public sealed class ApiClient(HttpClient httpClient, AuthService authService)
{
    public Task<HttpResponseMessage> GetAsync(string uri) => SendAsync(HttpMethod.Get, uri);

    public Task<HttpResponseMessage> PostAsync<T>(string uri, T payload) =>
        SendAsync(HttpMethod.Post, uri, payload);

    public Task<HttpResponseMessage> PatchAsync<T>(string uri, T payload) =>
        SendAsync(HttpMethod.Patch, uri, payload);

    private async Task<HttpResponseMessage> SendAsync<T>(HttpMethod method, string uri, T? payload = default)
    {
        using var request = new HttpRequestMessage(method, uri);
        var token = await authService.GetAccessTokenAsync();
        if (!string.IsNullOrWhiteSpace(token))
        {
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        }

        if (payload is not null)
        {
            request.Content = JsonContent.Create(payload);
        }

        return await httpClient.SendAsync(request);
    }

    private async Task<HttpResponseMessage> SendAsync(HttpMethod method, string uri)
    {
        using var request = new HttpRequestMessage(method, uri);
        var token = await authService.GetAccessTokenAsync();
        if (!string.IsNullOrWhiteSpace(token))
        {
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        }

        return await httpClient.SendAsync(request);
    }
}
