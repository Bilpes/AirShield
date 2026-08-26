using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;

var baseUrl = Environment.GetEnvironmentVariable("AIRSHIELD_URL") ?? "http://127.0.0.1:8080";
var token = Environment.GetEnvironmentVariable("AIRSHIELD_TOKEN") ?? "development-only";
using var client = new HttpClient { BaseAddress = new Uri(baseUrl) };
client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);

var sessionResponse = await client.PostAsJsonAsync("/v1/sessions", new {
    policy = "contact-center-eu-us-v1", language = "en", ttl_minutes = 60
});
sessionResponse.EnsureSuccessStatusCode();
var session = await sessionResponse.Content.ReadFromJsonAsync<JsonElement>();
var sessionId = session.GetProperty("session_id").GetString();

var response = await client.PostAsJsonAsync("/v1/protect", new {
    session_id = sessionId,
    text = "Customer called from +91 98765 43210 and email sana@example.com.",
    policy = "contact-center-eu-us-v1",
    destination = "approved-contact-center-llm",
    idempotency_key = Guid.NewGuid().ToString()
});
response.EnsureSuccessStatusCode();
Console.WriteLine(await response.Content.ReadAsStringAsync());
