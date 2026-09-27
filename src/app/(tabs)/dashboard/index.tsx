import * as Haptics from 'expo-haptics';
import { router } from 'expo-router';
import { useCallback, useEffect } from 'react';
import { Platform, RefreshControl, StyleSheet, Text, View } from 'react-native';

import {
  BodyBatteryCard,
  BriefingCard,
  DataSourceBadge,
  MetricTiles,
  RecoveryStrainCard,
  SleepCard,
} from '@/components/dashboard';
import { EmptyState, LoadingView, Screen } from '@/components/ui';
import { useCoachContext } from '@/hooks/useCoachContext';
import { useResponsiveLayout } from '@/hooks/useResponsiveLayout';
import { useCoachStore } from '@/store/coachStore';
import { useHealthStore } from '@/store/healthStore';
import { colors, spacing, typography } from '@/theme';
import { formatLongDate } from '@/utils/format';

export default function DashboardScreen() {
  const { status, error, mode, summaries, days, load } = useHealthStore();
  const { hasKey, loadBriefing } = useCoachStore();
  const ctx = useCoachContext();
  const { isTablet, columns } = useResponsiveLayout();
  const today = summaries.at(-1);
  const todayRaw = days.at(-1);

  useEffect(() => {
    if (status === 'ready' && hasKey && today) void loadBriefing(ctx);
  }, [status, hasKey, today, ctx, loadBriefing]);

  const refresh = useCallback(async () => {
    if (Platform.OS === 'ios') void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    await load();
  }, [load]);

  if (status === 'idle' || (status === 'loading' && !today)) return <LoadingView />;
  if (status === 'error' && !today) {
    return (
      <EmptyState
        symbol="exclamationmark.triangle.fill"
        tint={colors.strain}
        title="Daten konnten nicht geladen werden"
        message={error ?? ''}
        actionLabel="Einstellungen öffnen"
        onAction={() => router.navigate('/settings')}
      />
    );
  }
  if (!today) {
    return (
      <EmptyState
        symbol="heart.text.square"
        tint={colors.heart}
        title="Noch keine Daten"
        message="Verbinde Apple Health, importiere einen Export oder starte mit Demo-Daten."
        actionLabel="Datenquelle wählen"
        onAction={() => router.navigate('/settings')}
      />
    );
  }

  const header = (
    <View style={styles.header}>
      <Text style={styles.date}>{formatLongDate(today.date)}</Text>
      <DataSourceBadge mode={mode} />
    </View>
  );
  const hero = <RecoveryStrainCard summary={today} compact={!isTablet} />;
  const briefing = <BriefingCard onRefresh={() => void loadBriefing(ctx, true)} />;
  const sleep =
    today.sleep && todayRaw?.sleep ? (
      <SleepCard analysis={today.sleep} session={todayRaw.sleep} />
    ) : null;
  const battery = today.bodyBattery ? <BodyBatteryCard battery={today.bodyBattery} /> : null;
  const tiles = <MetricTiles summary={today} columns={isTablet ? 3 : 2} />;

  return (
    <Screen
      refreshControl={
        <RefreshControl
          refreshing={status === 'loading'}
          onRefresh={refresh}
          tintColor={colors.labelSecondary}
        />
      }
    >
      {header}
      {isTablet && columns >= 2 ? (
        <View style={styles.columns}>
          <View style={styles.column}>
            {hero}
            {briefing}
            {tiles}
          </View>
          <View style={styles.column}>
            {battery}
            {sleep}
          </View>
        </View>
      ) : (
        <>
          {hero}
          {briefing}
          {battery}
          {sleep}
          {tiles}
        </>
      )}
      <Text style={styles.disclaimer}>
        Pulse ist kein Medizinprodukt. Die Scores sind Schätzungen und ersetzen keine ärztliche
        Beratung.
      </Text>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { gap: spacing.sm },
  date: { ...typography.subheadline, color: colors.labelSecondary },
  columns: { flexDirection: 'row', gap: spacing.xl, alignItems: 'flex-start' },
  column: { flex: 1, gap: spacing.xl },
  disclaimer: {
    ...typography.caption2,
    color: colors.labelTertiary,
    textAlign: 'center',
    marginTop: spacing.lg,
  },
});
