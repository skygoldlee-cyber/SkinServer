import type { Survey } from "../lib/api";

// 라벨은 화면 표시용, 값은 계약(Survey) enum 과 일치.
const SKIN_TYPES: [string, string][] = [
  ["", "선택 안 함"], ["oily", "지성"], ["dry", "건성"],
  ["combination", "복합성"], ["normal", "중성"], ["sensitive", "민감성"],
];
const SENSITIVITY: [string, string][] = [
  ["stings_easily", "쉽게 따갑거나 화끈거려요"],
  ["reacts_to_products", "화장품에 자주 반응해요"],
  ["redness_frequent", "붉어짐이 잦아요"],
];
const CONCERNS: [string, string][] = [
  ["acne", "트러블"], ["pigmentation", "색소·잡티"], ["wrinkles", "주름"],
  ["pores", "모공"], ["redness", "붉은기"], ["dryness", "건조"],
];
const AGE_BANDS: [string, string][] = [
  ["", "선택 안 함"], ["10s", "10대"], ["20s", "20대"],
  ["30s", "30대"], ["40s", "40대"], ["50s+", "50대 이상"],
];
const SUN: [string, string][] = [
  ["", "선택 안 함"], ["low", "낮음"], ["medium", "보통"], ["high", "높음"],
];

export function SurveyForm({ value, onChange }: { value: Survey; onChange: (s: Survey) => void }) {
  const set = (patch: Partial<Survey>) => onChange({ ...value, ...patch });

  const toggleConcern = (key: string) => {
    const cur = value.concerns ?? [];
    set({ concerns: cur.includes(key) ? cur.filter((c) => c !== key) : [...cur, key] });
  };
  const toggleSens = (key: string) => {
    const cur = value.sensitivity ?? {};
    set({ sensitivity: { ...cur, [key]: !cur[key] } });
  };

  return (
    <fieldset className="survey">
      <legend>설문 <span className="muted">선택 — 채울수록 처방이 정확해져요</span></legend>

      <label className="field">
        <span>피부 타입</span>
        <select value={value.skin_type ?? ""}
                onChange={(e) => set({ skin_type: e.target.value || undefined })}>
          {SKIN_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
      </label>

      <div className="field">
        <span>민감 반응</span>
        <div className="checks">
          {SENSITIVITY.map(([k, l]) => (
            <label key={k} className="check">
              <input type="checkbox" checked={!!value.sensitivity?.[k]} onChange={() => toggleSens(k)} />
              {l}
            </label>
          ))}
        </div>
      </div>

      <div className="field">
        <span>고민 <span className="muted">복수 선택</span></span>
        <div className="chips">
          {CONCERNS.map(([k, l]) => {
            const on = (value.concerns ?? []).includes(k);
            return (
              <button type="button" key={k} className={on ? "chip on" : "chip"}
                      aria-pressed={on} onClick={() => toggleConcern(k)}>{l}</button>
            );
          })}
        </div>
      </div>

      <label className="field">
        <span>연령대</span>
        <select value={value.age_band ?? ""}
                onChange={(e) => set({ age_band: e.target.value || undefined })}>
          {AGE_BANDS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
      </label>

      <label className="field">
        <span>햇빛 노출</span>
        <select value={value.sun_exposure ?? ""}
                onChange={(e) => set({ sun_exposure: e.target.value || undefined })}>
          {SUN.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
      </label>

      <label className="field">
        <span>기타 메모</span>
        <textarea rows={2} value={value.notes ?? ""}
                  onChange={(e) => set({ notes: e.target.value })} />
      </label>
    </fieldset>
  );
}

// 빈 값은 제거해 계약(Survey) shape 로 정리. 아무것도 안 채웠으면 undefined → survey 미전송.
export function cleanSurvey(s: Survey): Survey | undefined {
  const out: Survey = {};
  if (s.skin_type) out.skin_type = s.skin_type;
  if (s.sensitivity) {
    const sens: Record<string, boolean> = {};
    for (const [k, v] of Object.entries(s.sensitivity)) if (v) sens[k] = true;
    if (Object.keys(sens).length) out.sensitivity = sens;
  }
  if (s.concerns && s.concerns.length) out.concerns = s.concerns;
  if (s.age_band) out.age_band = s.age_band;
  if (s.sun_exposure) out.sun_exposure = s.sun_exposure;
  if (s.notes && s.notes.trim()) out.notes = s.notes.trim();
  return Object.keys(out).length ? out : undefined;
}
