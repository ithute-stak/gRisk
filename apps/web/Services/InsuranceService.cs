using System.Net;
using System.Net.Http.Json;
using gRisk.Web.Models;

namespace gRisk.Web.Services;

public sealed class InsuranceService(ApiClient apiClient)
{
    public async Task<List<InsuranceProductModel>> GetProductsAsync()
    {
        using var response = await apiClient.GetAsync("api/v1/insurance/products");
        await EnsureSuccessAsync(response);
        return await response.Content.ReadFromJsonAsync<List<InsuranceProductModel>>() ?? [];
    }

    public async Task<CustomerListResponse> GetCustomersAsync(string? search = null)
    {
        var query = "api/v1/customers?page=1&page_size=100";
        if (!string.IsNullOrWhiteSpace(search))
        {
            query += $"&q={Uri.EscapeDataString(search.Trim())}";
        }

        using var response = await apiClient.GetAsync(query);
        await EnsureSuccessAsync(response);
        return await response.Content.ReadFromJsonAsync<CustomerListResponse>() ?? new CustomerListResponse();
    }

    public async Task<QuoteListModel> GetQuotesAsync(string? search = null, string? status = null)
    {
        var query = "api/v1/insurance/quotes?page=1&page_size=100";
        if (!string.IsNullOrWhiteSpace(search))
        {
            query += $"&q={Uri.EscapeDataString(search.Trim())}";
        }
        if (!string.IsNullOrWhiteSpace(status))
        {
            query += $"&quote_status={Uri.EscapeDataString(status)}";
        }

        using var response = await apiClient.GetAsync(query);
        await EnsureSuccessAsync(response);
        return await response.Content.ReadFromJsonAsync<QuoteListModel>() ?? new QuoteListModel();
    }

    public async Task<QuoteModel> CreateQuoteAsync(CreateQuoteRequest request)
    {
        using var response = await apiClient.PostAsync("api/v1/insurance/quotes", request);
        await EnsureSuccessAsync(response);
        return (await response.Content.ReadFromJsonAsync<QuoteModel>())!;
    }

    public async Task<QuoteModel> UpdateQuoteStatusAsync(Guid quoteId, string status)
    {
        using var response = await apiClient.PatchAsync(
            $"api/v1/insurance/quotes/{quoteId}/status",
            new QuoteStatusRequest { Status = status });
        await EnsureSuccessAsync(response);
        return (await response.Content.ReadFromJsonAsync<QuoteModel>())!;
    }

    public async Task<PolicyModel> ConvertToPolicyAsync(Guid quoteId, DateOnly startDate, DateOnly endDate)
    {
        using var response = await apiClient.PostAsync(
            $"api/v1/insurance/quotes/{quoteId}/convert-to-policy",
            new ConvertQuoteRequest { StartDate = startDate, EndDate = endDate });
        await EnsureSuccessAsync(response);
        return (await response.Content.ReadFromJsonAsync<PolicyModel>())!;
    }

    public async Task<List<PolicyModel>> GetPoliciesAsync()
    {
        using var response = await apiClient.GetAsync("api/v1/insurance/policies");
        await EnsureSuccessAsync(response);
        return await response.Content.ReadFromJsonAsync<List<PolicyModel>>() ?? [];
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
