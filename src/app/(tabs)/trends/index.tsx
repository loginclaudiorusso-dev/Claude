import { PlaceholderCard, Screen } from '@/components/ui';
import { colors } from '@/theme';

export default function TrendsScreen() {
  return (
    <Screen>
      <PlaceholderCard
        symbol="waveform.path.ecg"
        title="HRV-Trend"
        subtitle="SDNN vs. 7-Tage-Baseline · 7 / 30 Tage"
        tint={colors.hrv}
      />
      <PlaceholderCard
        symbol="moon.stars.fill"
        title="Schlafarchitektur"
        subtitle="Tief-, REM-, Kern- & Wachphasen"
        tint={colors.sleep}
      />
      <PlaceholderCard
        symbol="figure.run"
        title="Trainingsbelastung"
        subtitle="Tages-Strain & akute/chronische Last"
        tint={colors.strain}
      />
    </Screen>
  );
}
