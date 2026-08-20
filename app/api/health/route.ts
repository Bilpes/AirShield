import { NextResponse } from "next/server";
import {
  controlPlaneConfigured,
  controlPlaneFetch,
  productionMode,
} from "@/lib/server/control-plane";

export const runtime = "nodejs";

export async function GET() {
  if (controlPlaneConfigured()) {
    try {
      const upstream = await controlPlaneFetch("/v1/health/ready");
      return NextResponse.json(await upstream.json(), { status: upstream.status });
    } catch {
      return NextResponse.json({ status: "not_ready", control_plane: "unreachable" }, { status: 503 });
    }
  }
  if (productionMode) {
    return NextResponse.json({ status: "not_ready", control_plane: "not_configured" }, { status: 503 });
  }
  return NextResponse.json({
    status: "healthy",
    app: "airshield-next",
    version: "1.0.0",
    language: "en",
    mode: "development-prototype",
    paid_speech_api: false,
  });
}
