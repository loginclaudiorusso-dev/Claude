import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import {
  Icon,
  PressableScale,
  Screen,
  SegmentedControl,
  Separator,
  SettingsRow,
  SettingsSection,
} from '@/components/ui';
import { CLAUDE_MODEL } from '@/config/claude';
import {
  CoachError,
  clearBriefingCache,
  deleteApiKey,
  getApiKey,
  maskApiKey,
  saveApiKey,
  validateApiKey,
} from '@/services/claudeCoach';
import { isHealthKitAvailable, requestHealthKitPermissions } from '@/services/health';
import { useCoachStore } from '@/store/coachStore';
import { useHealthStore } from '@/store/healthStore';
import { useSettingsStore } from '@/store/settingsStore';
import type { BiologicalSex } from '@/types/health';
import { colors, palette, radius, spacing, typography } from '@/theme';
import { formatDuration } from '@/utils/format';

const message = (e: unknown) => (e instanceof Error ? e.message : 'Unbekannter Fehler');

function ApiKeySection() {
  const refreshKeyStatus = useCoachStore((s) => s.refreshKeyStatus);
  const [masked, setMasked] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const reload = () => setVersion((v) => v + 1);

  useEffect(() => {
    let active = true;
    void getApiKey().then((key) => {
      if (active) setMasked(key ? maskApiKey(key) : null);
    });
    return () => {
      active = false;
    };
  }, [version]);

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      const key = input.trim();
      await validateApiKey(key);
      await saveApiKey(key);
      setInput('');
      reload();
      await refreshKeyStatus();
    } catch (e) {
      setError(e instanceof CoachError ? e.message : message(e));
    } finally {
      setBusy(false);
    }
  };

  const remove = () =>
    Alert.alert('API-Key entfernen?', 'Der Coach ist danach deaktiviert.', [
      { text: 'Abbrechen', style: 'cancel' },
      {
        text: 'Entfernen',
        style: 'destructive',
        onPress: async () => {
          await deleteApiKey();
          clearBriefingCache();
          useCoachStore.getState().resetChat();
          reload();
          await refreshKeyStatus();
        },
      },
    ]);

  return (
    <SettingsSection
      title="Claude AI Coach"
      footer={`Modell: ${CLAUDE_MODEL}. Der Key wird nur im Schlüsselbund dieses Geräts gespeichert und direkt an die Anthropic API gesendet. An Claude gehen nur Tageswerte, keine Rohdaten.`}
    >
      {masked ? (
        <>
          <SettingsRow
            symbol="key.fill"
            tint={colors.coach}
            title="API-Key hinterlegt"
            subtitle={masked}
            accessory={<Icon name="checkmark.seal.fill" size={18} color={palette.green} />}
          />
          <Separator />
          <SettingsRow
            symbol="trash.fill"
            tint={palette.red}
            title="API-Key entfernen"
            destructive
            onPress={remove}
          />
        </>
      ) : (
        <View style={styles.keyForm}>
          <TextInput
            style={styles.input}
            value={input}
            onChangeText={setInput}
            placeholder="sk-ant-…"
            placeholderTextColor={colors.labelTertiary}
            secureTextEntry
            autoCapitalize="none"
            autoCorrect={false}
            textContentType="none"
            accessibilityLabel="Anthropic API-Key"
          />
          {error ? <Text style={styles.error}>{error}</Text> : null}
          <PressableScale
            onPress={save}
            disabled={busy || input.trim().length < 20}
            style={[styles.button, (busy || input.trim().length < 20) && styles.buttonDisabled]}
            accessibilityRole="button"
          >
            {busy ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>Prüfen & speichern</Text>
            )}
          </PressableScale>
        </View>
      )}
    </SettingsSection>
  );
}

function DataSourceSection() {
  const { mode, load, importFile, status } = useHealthStore();
  const setHealthKitConnected = useSettingsStore((s) => s.setHealthKitConnected);
  const [hkAvailable, setHkAvailable] = useState<boolean | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    void isHealthKitAvailable().then(setHkAvailable);
  }, []);

  const run = async (key: string, fn: () => Promise<void>) => {
    setBusy(key);
    try {
      await fn();
    } catch (e) {
      Alert.alert('Fehler', message(e));
    } finally {
      setBusy(null);
    }
  };

  const connectHealth = () =>
    run('healthkit', async () => {
      await requestHealthKitPermissions();
      setHealthKitConnected(true);
      await load('healthkit');
    });

  const doImport = () =>
    run('import', async () => {
      const result = await importFile();
      if (result)
        Alert.alert(
          'Import abgeschlossen',
          `${result.importedDays} Tage aus „${result.fileName}“ importiert.`,
        );
    });

  const check = (m: string) =>
    busy === m ? (
      <ActivityIndicator color={colors.labelSecondary} />
    ) : mode === m ? (
      <Icon name="checkmark" size={16} color={colors.tint} weight="bold" />
    ) : undefined;

  return (
    <SettingsSection
      title="Datenquelle"
      footer="Pulse liest Gesundheitsdaten nur lesend. Importe unterstützen JSON- und CSV-Exporte der App „Health Auto Export“."
    >
      <SettingsRow
        symbol="heart.fill"
        tint={palette.pink}
        title="Apple Health"
        subtitle={
          hkAvailable === false
            ? Platform.OS === 'ios'
              ? 'Nur im Development Build verfügbar'
              : 'Nur auf dem iPhone verfügbar'
            : 'HRV, Ruhepuls, Schlaf, Aktivität, Workouts'
        }
        onPress={connectHealth}
        disabled={hkAvailable === false || busy !== null}
        accessory={check('healthkit')}
      />
      <Separator />
      <SettingsRow
        symbol="square.and.arrow.down.fill"
        tint={palette.blue}
        title="Export importieren"
        subtitle="JSON oder CSV aus Dateien, iCloud, AirDrop"
        onPress={doImport}
        disabled={busy !== null}
        accessory={check('import')}
      />
      <Separator />
      <SettingsRow
        symbol="wand.and.stars"
        tint={palette.orange}
        title="Demo-Daten"
        subtitle="45 Tage Beispieldaten"
        onPress={() => run('demo', () => load('demo'))}
        disabled={busy !== null || status === 'loading'}
        accessory={check('demo')}
      />
    </SettingsSection>
  );
}

function ProfileSection() {
  const { profile, setProfile } = useSettingsStore();
  const recompute = useHealthStore((s) => s.recompute);
  const [birthYear, setBirthYear] = useState(profile.birthYear ? String(profile.birthYear) : '');
  const [maxHr, setMaxHr] = useState(profile.maxHeartRate ? String(profile.maxHeartRate) : '');
  const sleepNeed = profile.sleepNeedMinutes ?? 480;

  const update = (patch: Parameters<typeof setProfile>[0]) => {
    setProfile(patch);
    recompute();
  };

  const commitNumber = (
    raw: string,
    key: 'birthYear' | 'maxHeartRate',
    min: number,
    max: number,
  ) => {
    const n = Number(raw);
    update({
      [key]: raw === '' || !Number.isFinite(n) || n < min || n > max ? undefined : Math.round(n),
    });
  };

  return (
    <SettingsSection
      title="Profil"
      footer="Alter und maximale Herzfrequenz bestimmen deine Pulszonen; der Schlafbedarf ist die Basis für Schlafschuld und Empfehlungen."
    >
      <View style={styles.field}>
        <Text style={styles.fieldLabel}>Geburtsjahr</Text>
        <TextInput
          style={styles.fieldInput}
          value={birthYear}
          onChangeText={setBirthYear}
          onEndEditing={() =>
            commitNumber(birthYear, 'birthYear', 1900, new Date().getFullYear() - 10)
          }
          keyboardType="number-pad"
          placeholder="z. B. 1990"
          placeholderTextColor={colors.labelTertiary}
          maxLength={4}
        />
      </View>
      <Separator />
      <View style={styles.field}>
        <Text style={styles.fieldLabel}>Max. Herzfrequenz</Text>
        <TextInput
          style={styles.fieldInput}
          value={maxHr}
          onChangeText={setMaxHr}
          onEndEditing={() => commitNumber(maxHr, 'maxHeartRate', 120, 230)}
          keyboardType="number-pad"
          placeholder="automatisch"
          placeholderTextColor={colors.labelTertiary}
          maxLength={3}
        />
      </View>
      <Separator />
      <View style={styles.fieldColumn}>
        <Text style={styles.fieldLabel}>Geschlecht (für Belastungsformel)</Text>
        <SegmentedControl<BiologicalSex>
          options={[
            { value: 'female', label: 'Weiblich' },
            { value: 'male', label: 'Männlich' },
            { value: 'other', label: 'Divers' },
          ]}
          value={profile.sex ?? 'other'}
          onChange={(sex) => update({ sex })}
        />
      </View>
      <Separator />
      <View style={styles.field}>
        <Text style={styles.fieldLabel}>Schlafbedarf</Text>
        <View style={styles.stepper}>
          <PressableScale
            onPress={() => update({ sleepNeedMinutes: Math.max(360, sleepNeed - 15) })}
            style={styles.stepButton}
            accessibilityLabel="Weniger Schlafbedarf"
          >
            <Icon name="minus" size={14} color={colors.label} />
          </PressableScale>
          <Text style={styles.stepValue}>{formatDuration(sleepNeed)}</Text>
          <PressableScale
            onPress={() => update({ sleepNeedMinutes: Math.min(600, sleepNeed + 15) })}
            style={styles.stepButton}
            accessibilityLabel="Mehr Schlafbedarf"
          >
            <Icon name="plus" size={14} color={colors.label} />
          </PressableScale>
        </View>
      </View>
    </SettingsSection>
  );
}

function PrivacySection() {
  const deleteLocalData = useHealthStore((s) => s.deleteLocalData);
  const confirmDelete = () =>
    Alert.alert(
      'Lokale Daten löschen?',
      'Importierte und zwischengespeicherte Gesundheitsdaten sowie Briefings werden von diesem Gerät entfernt. Apple Health bleibt unverändert.',
      [
        { text: 'Abbrechen', style: 'cancel' },
        {
          text: 'Löschen',
          style: 'destructive',
          onPress: async () => {
            clearBriefingCache();
            useCoachStore.getState().resetChat();
            await deleteLocalData();
          },
        },
      ],
    );
  return (
    <SettingsSection
      title="Datenschutz"
      footer="Pulse ist kein Medizinprodukt. Alle Scores sind Schätzungen und ersetzen keine ärztliche Beratung."
    >
      <SettingsRow
        symbol="trash.fill"
        tint={palette.red}
        title="Lokale Daten löschen"
        destructive
        onPress={confirmDelete}
      />
    </SettingsSection>
  );
}

export default function SettingsScreen() {
  return (
    <Screen keyboardShouldPersistTaps="handled" keyboardDismissMode="interactive">
      <ApiKeySection />
      <DataSourceSection />
      <ProfileSection />
      <PrivacySection />
    </Screen>
  );
}

const styles = StyleSheet.create({
  keyForm: { padding: spacing.lg, gap: spacing.md },
  input: {
    ...typography.body,
    color: colors.label,
    backgroundColor: colors.surfaceSecondary,
    borderRadius: radius.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
  },
  error: { ...typography.footnote, color: palette.red },
  button: {
    backgroundColor: colors.coach,
    borderRadius: radius.sm,
    paddingVertical: spacing.md,
    alignItems: 'center',
  },
  buttonDisabled: { opacity: 0.4 },
  buttonText: { ...typography.headline, color: '#fff' },
  field: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    minHeight: 52,
    gap: spacing.md,
  },
  fieldColumn: { paddingHorizontal: spacing.lg, paddingVertical: spacing.md, gap: spacing.sm },
  fieldLabel: { ...typography.body, color: colors.label, flex: 1 },
  fieldInput: {
    ...typography.body,
    color: colors.labelSecondary,
    textAlign: 'right',
    minWidth: 110,
    paddingVertical: spacing.sm,
  },
  stepper: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  stepButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: colors.surfaceSecondary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepValue: {
    ...typography.body,
    color: colors.label,
    minWidth: 90,
    textAlign: 'center',
    fontVariant: ['tabular-nums'],
  },
});
