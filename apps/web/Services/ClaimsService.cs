using System.Net;
using System.Net.Http.Json;
using gRisk.Web.Models;

namespace gRisk.Web.Services;

public sealed class ClaimsService(ApiClient apiClient)
{
    public async Task<ClaimListModel> GetClaimsAsync(string? search = null, string? status = null)
    {
        var query = "api/v1/claims?page=1&page_size=100";
        if (!string.IsNullOrWhiteSpace(search))
        {
            query += $"&q={Uri.EscapeDataString(search.Trim())}";
        }
        if (!string.IsNullOrWhiteSpace(status))
        {
            query += $"&claim_status={Uri.EscapeDataString(status)}";
        }

        using var response = await apiClient.GetAsync(query);
        await EnsureSuccessAsync(response);
        return await response.Content.ReadFromJsonAsync<ClaimListModel>() ?? new ClaimListModel();
    }

    public async Task<ClaimModel> CreateClaimAsync(CreateClaimRequest request)
    {
        using var response = await apiClient.PostAsync("api/v1/claims", request);
        await EnsureSuccessAsync(response);
        return (await response.Content.ReadFromJsonAsync<ClaimModel>())!;
    }

    public async Task<ClaimModel> UpdateStatusAsync(
        Guid claimId,
        string status,
        string? note = null,
        decimal? approvedAmount = null)
    {
        using var response = await apiClient.PatchAsync(
            $"api/v1/claims/{claimId}/status",
            new ClaimStatusRequest
            {
                Status = status,
                Note = note,
                ApprovedAmount = approvedAmount
            });
        await EnsureSuccessAsync(response);
        return (await response.Content.ReadFromJsonAsync<ClaimModel>())!;
    }

    public async Task<ClaimEventModel> AddNoteAsync(Guid claimId, string note)
    {
        using var response = await apiClient.PostAsync(
            $"api/v1/claims/{claimId}/notes",
            new ClaimNoteRequest { Note = note });
        await EnsureSuccessAsync(response);
        return (await response.Content.ReadFromJsonAsync<ClaimEventModel>())!;
    }

    private static async Task EnsureSuccessAsync(HttpResponseMessage response)
    {
        if (response.IsSuccessStatusCode)
        {
            return;
        }

        var body = await response.Content.ReadAsStringAsync();
        if (response.StatusCode == HttpStatusCode.Unauthorized)
        {
            throw new InvalidOperationException("Your session has expired. Please sign in again.");
        }

        throw new InvalidOperationException(
            string.IsNullOrWhiteSpace(body)
                ? $"gRisk API request failed ({(int)response.StatusCode})."
                : body);
    }
}
