package main

import (
  "bytes"
  "crypto/rand"
  "encoding/hex"
  "encoding/json"
  "fmt"
  "io"
  "net/http"
  "os"
)

func post(baseURL, token, path string, body any) map[string]any {
  encoded, _ := json.Marshal(body)
  req, _ := http.NewRequest("POST", baseURL+path, bytes.NewReader(encoded))
  req.Header.Set("Authorization", "Bearer "+token)
  req.Header.Set("Content-Type", "application/json")
  resp, err := http.DefaultClient.Do(req)
  if err != nil { panic(err) }
  defer resp.Body.Close()
  output, _ := io.ReadAll(resp.Body)
  if resp.StatusCode/100 != 2 { panic(string(output)) }
  var result map[string]any
  if err := json.Unmarshal(output, &result); err != nil { panic(err) }
  return result
}

func main() {
  baseURL := os.Getenv("AIRSHIELD_URL")
  if baseURL == "" { baseURL = "http://127.0.0.1:8080" }
  token := os.Getenv("AIRSHIELD_TOKEN")
  if token == "" { token = "development-only" }
  session := post(baseURL, token, "/v1/sessions", map[string]any{
    "policy": "insurance-eu-us-v1", "language": "en", "ttl_minutes": 60,
  })
  nonce := make([]byte, 16); _, _ = rand.Read(nonce)
  result := post(baseURL, token, "/v1/protect", map[string]any{
    "session_id": session["session_id"],
    "text": "The claimant email is vikram@example.com.",
    "policy": "insurance-eu-us-v1",
    "destination": "approved-insurance-llm",
    "idempotency_key": hex.EncodeToString(nonce),
  })
  fmt.Println(result["protected_text"])
}
