import { CampaignOverride } from "./CampaignOverride";
import { EmergencyOverride } from "./EmergencyOverride";
import { ManualOverride } from "./ManualOverride";
import { QueueCallOverride } from "./QueueCallOverride";
import type { ScreenOverride } from "./overrideTypes";

type Props = {
  override: ScreenOverride | null;
};

/**
 * Maps override_type → visual. Unknown types are ignored (player stays up).
 * LayoutResolver remains mounted underneath.
 */
export function OverrideRenderer({ override }: Props) {
  if (!override) return null;

  const type = (override.override_type || "").toUpperCase();
  switch (type) {
    case "QUEUE_CALL":
      return <QueueCallOverride override={override} />;
    case "EMERGENCY":
      return <EmergencyOverride override={override} />;
    case "MANUAL":
      return <ManualOverride override={override} />;
    case "CAMPAIGN":
      return <CampaignOverride override={override} />;
    default:
      console.warn("[display] unknown override_type", type);
      return null;
  }
}
