using System.Text.Json.Serialization;

namespace gRisk.Web.Models;

public sealed class CustomerListResponse
{
    [JsonPropertyName("items")]
    public List<CustomerSummary> Items { get; set; } = [];

    [JsonPropertyName("total")]
    public int Total { get; set; }

    [JsonPropertyName("page")]
    public int Page { get; set; }

    [JsonPropertyName("page_size")]
    public int PageSize { get; set; }
}

public sealed class CustomerSummary
{
    [JsonPropertyName("id")]
    public Guid Id { get; set; }

    [JsonPropertyName("customer_number")]
    public string CustomerNumber { get; set; } = string.Empty;

    [JsonPropertyName("customer_type")]
    public string CustomerType { get; set; } = string.Empty;

    [JsonPropertyName("display_name")]
    public string DisplayName { get; set; } = string.Empty;

    [JsonPropertyName("email")]
    public string? Email { get; set; }

    [JsonPropertyName("phone")]
    public string? Phone { get; set; }

    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;

    [JsonPropertyName("created_at")]
    public DateTimeOffset CreatedAt { get; set; }
}

public sealed class CreateCustomerRequest
{
    [JsonPropertyName("customer_type")]
    public string CustomerType { get; set; } = "company";

    [JsonPropertyName("display_name")]
    public string? DisplayName { get; set; }

    [JsonPropertyName("first_name")]
    public string? FirstName { get; set; }

    [JsonPropertyName("last_name")]
    public string? LastName { get; set; }

    [JsonPropertyName("company_name")]
    public string? CompanyName { get; set; }

    [JsonPropertyName("registration_number")]
    public string? RegistrationNumber { get; set; }

    [JsonPropertyName("tax_number")]
    public string? TaxNumber { get; set; }

    [JsonPropertyName("email")]
    public string? Email { get; set; }

    [JsonPropertyName("phone")]
    public string? Phone { get; set; }

    [JsonPropertyName("status")]
    public string Status { get; set; } = "active";
}
