using System.Text.Json.Serialization;

namespace gRisk.Web.Models;

public sealed class InsuranceProductModel
{
    [JsonPropertyName("id")]
    public Guid Id { get; set; }

    [JsonPropertyName("code")]
    public string Code { get; set; } = string.Empty;

    [JsonPropertyName("name")]
    public string Name { get; set; } = string.Empty;

    [JsonPropertyName("category")]
    public string Category { get; set; } = string.Empty;

    [JsonPropertyName("description")]
    public string? Description { get; set; }

    [JsonPropertyName("is_active")]
    public bool IsActive { get; set; }
}

public sealed class QuoteItemModel
{
    [JsonPropertyName("id")]
    public Guid Id { get; set; }

    [JsonPropertyName("label")]
    public string Label { get; set; } = string.Empty;

    [JsonPropertyName("description")]
    public string? Description { get; set; }

    [JsonPropertyName("amount")]
    public decimal Amount { get; set; }
}

public sealed class QuoteModel
{
    [JsonPropertyName("id")]
    public Guid Id { get; set; }

    [JsonPropertyName("quote_number")]
    public string QuoteNumber { get; set; } = string.Empty;

    [JsonPropertyName("customer_id")]
    public Guid CustomerId { get; set; }

    [JsonPropertyName("product_id")]
    public Guid ProductId { get; set; }

    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;

    [JsonPropertyName("currency")]
    public string Currency { get; set; } = "LSL";

    [JsonPropertyName("sum_insured")]
    public decimal SumInsured { get; set; }

    [JsonPropertyName("premium")]
    public decimal Premium { get; set; }

    [JsonPropertyName("third_party_limit")]
    public decimal? ThirdPartyLimit { get; set; }

    [JsonPropertyName("start_date")]
    public DateOnly? StartDate { get; set; }

    [JsonPropertyName("end_date")]
    public DateOnly? EndDate { get; set; }

    [JsonPropertyName("notes")]
    public string? Notes { get; set; }

    [JsonPropertyName("created_at")]
    public DateTimeOffset CreatedAt { get; set; }

    [JsonPropertyName("updated_at")]
    public DateTimeOffset UpdatedAt { get; set; }

    [JsonPropertyName("items")]
    public List<QuoteItemModel> Items { get; set; } = [];
}

public sealed class QuoteListModel
{
    [JsonPropertyName("items")]
    public List<QuoteModel> Items { get; set; } = [];

    [JsonPropertyName("total")]
    public int Total { get; set; }

    [JsonPropertyName("page")]
    public int Page { get; set; }

    [JsonPropertyName("page_size")]
    public int PageSize { get; set; }
}

public sealed class PolicyModel
{
    [JsonPropertyName("id")]
    public Guid Id { get; set; }

    [JsonPropertyName("policy_number")]
    public string PolicyNumber { get; set; } = string.Empty;

    [JsonPropertyName("customer_id")]
    public Guid CustomerId { get; set; }

    [JsonPropertyName("product_id")]
    public Guid ProductId { get; set; }

    [JsonPropertyName("source_quote_id")]
    public Guid? SourceQuoteId { get; set; }

    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;

    [JsonPropertyName("currency")]
    public string Currency { get; set; } = "LSL";

    [JsonPropertyName("sum_insured")]
    public decimal SumInsured { get; set; }

    [JsonPropertyName("premium")]
    public decimal Premium { get; set; }

    [JsonPropertyName("start_date")]
    public DateOnly StartDate { get; set; }

    [JsonPropertyName("end_date")]
    public DateOnly EndDate { get; set; }

    [JsonPropertyName("created_at")]
    public DateTimeOffset CreatedAt { get; set; }
}

public sealed class CreateQuoteRequest
{
    [JsonPropertyName("customer_id")]
    public Guid CustomerId { get; set; }

    [JsonPropertyName("product_id")]
    public Guid ProductId { get; set; }

    [JsonPropertyName("currency")]
    public string Currency { get; set; } = "LSL";

    [JsonPropertyName("sum_insured")]
    public decimal SumInsured { get; set; }

    [JsonPropertyName("premium")]
    public decimal Premium { get; set; }

    [JsonPropertyName("third_party_limit")]
    public decimal? ThirdPartyLimit { get; set; }

    [JsonPropertyName("start_date")]
    public DateOnly? StartDate { get; set; }

    [JsonPropertyName("end_date")]
    public DateOnly? EndDate { get; set; }

    [JsonPropertyName("notes")]
    public string? Notes { get; set; }

    [JsonPropertyName("items")]
    public List<CreateQuoteItemRequest> Items { get; set; } = [];
}

public sealed class CreateQuoteItemRequest
{
    [JsonPropertyName("label")]
    public string Label { get; set; } = string.Empty;

    [JsonPropertyName("description")]
    public string? Description { get; set; }

    [JsonPropertyName("amount")]
    public decimal Amount { get; set; }
}

public sealed class QuoteStatusRequest
{
    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;
}

public sealed class ConvertQuoteRequest
{
    [JsonPropertyName("start_date")]
    public DateOnly StartDate { get; set; }

    [JsonPropertyName("end_date")]
    public DateOnly EndDate { get; set; }
}
