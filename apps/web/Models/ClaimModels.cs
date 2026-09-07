using System.Text.Json.Serialization;

namespace gRisk.Web.Models;

public sealed class ClaimEventModel
{
    [JsonPropertyName("id")]
    public Guid Id { get; set; }

    [JsonPropertyName("event_type")]
    public string EventType { get; set; } = string.Empty;

    [JsonPropertyName("note")]
    public string? Note { get; set; }

    [JsonPropertyName("from_status")]
    public string? FromStatus { get; set; }

    [JsonPropertyName("to_status")]
    public string? ToStatus { get; set; }

    [JsonPropertyName("created_at")]
    public DateTimeOffset CreatedAt { get; set; }
}

public sealed class ClaimModel
{
    [JsonPropertyName("id")]
    public Guid Id { get; set; }

    [JsonPropertyName("claim_number")]
    public string ClaimNumber { get; set; } = string.Empty;

    [JsonPropertyName("policy_id")]
    public Guid PolicyId { get; set; }

    [JsonPropertyName("customer_id")]
    public Guid CustomerId { get; set; }

    [JsonPropertyName("claim_type")]
    public string ClaimType { get; set; } = string.Empty;

    [JsonPropertyName("incident_date")]
    public DateOnly IncidentDate { get; set; }

    [JsonPropertyName("description")]
    public string Description { get; set; } = string.Empty;

    [JsonPropertyName("claim_amount")]
    public decimal ClaimAmount { get; set; }

    [JsonPropertyName("approved_amount")]
    public decimal? ApprovedAmount { get; set; }

    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;

    [JsonPropertyName("priority")]
    public string Priority { get; set; } = string.Empty;

    [JsonPropertyName("reported_at")]
    public DateTimeOffset ReportedAt { get; set; }

    [JsonPropertyName("created_at")]
    public DateTimeOffset CreatedAt { get; set; }

    [JsonPropertyName("updated_at")]
    public DateTimeOffset UpdatedAt { get; set; }

    [JsonPropertyName("events")]
    public List<ClaimEventModel> Events { get; set; } = [];
}

public sealed class ClaimListModel
{
    [JsonPropertyName("items")]
    public List<ClaimModel> Items { get; set; } = [];

    [JsonPropertyName("total")]
    public int Total { get; set; }

    [JsonPropertyName("page")]
    public int Page { get; set; }

    [JsonPropertyName("page_size")]
    public int PageSize { get; set; }
}

public sealed class CreateClaimRequest
{
    [JsonPropertyName("policy_id")]
    public Guid PolicyId { get; set; }

    [JsonPropertyName("claim_type")]
    public string ClaimType { get; set; } = "general";

    [JsonPropertyName("incident_date")]
    public DateOnly IncidentDate { get; set; }

    [JsonPropertyName("description")]
    public string Description { get; set; } = string.Empty;

    [JsonPropertyName("claim_amount")]
    public decimal ClaimAmount { get; set; }

    [JsonPropertyName("priority")]
    public string Priority { get; set; } = "normal";
}

public sealed class ClaimStatusRequest
{
    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;

    [JsonPropertyName("note")]
    public string? Note { get; set; }

    [JsonPropertyName("approved_amount")]
    public decimal? ApprovedAmount { get; set; }
}

public sealed class ClaimNoteRequest
{
    [JsonPropertyName("note")]
    public string Note { get; set; } = string.Empty;
}
