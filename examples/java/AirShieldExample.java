import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class AirShieldExample {
  private static final HttpClient CLIENT = HttpClient.newBuilder().version(HttpClient.Version.HTTP_1_1).build();
  private static final String BASE = System.getenv().getOrDefault("AIRSHIELD_URL", "http://127.0.0.1:8080");
  private static final String TOKEN = System.getenv().getOrDefault("AIRSHIELD_TOKEN", "development-only");

  private static String post(String path, String json) throws Exception {
    HttpRequest request = HttpRequest.newBuilder().uri(URI.create(BASE + path))
      .header("Authorization", "Bearer " + TOKEN).header("Content-Type", "application/json")
      .POST(HttpRequest.BodyPublishers.ofString(json)).build();
    HttpResponse<String> response = CLIENT.send(request, HttpResponse.BodyHandlers.ofString());
    if (response.statusCode() / 100 != 2) throw new IllegalStateException(response.body());
    return response.body();
  }

  public static void main(String[] args) throws Exception {
    String session = post("/v1/sessions", "{\"policy\":\"healthcare-us-eu-v1\",\"language\":\"en\",\"ttl_minutes\":60}");
    Matcher match = Pattern.compile("\\\"session_id\\\":\\\"([^\\\"]+)\\\"").matcher(session);
    if (!match.find()) throw new IllegalStateException("No session_id in response");
    String json = "{\"session_id\":\"" + match.group(1) + "\","
      + "\"text\":\"MRN BLR-482791 belongs to the patient.\","
      + "\"policy\":\"healthcare-us-eu-v1\",\"destination\":\"approved-health-llm\","
      + "\"idempotency_key\":\"" + UUID.randomUUID() + "\"}";
    System.out.println(post("/v1/protect", json));
  }
}
