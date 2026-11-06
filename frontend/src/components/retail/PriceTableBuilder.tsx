import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Drawer,
  Input,
  Select,
  Badge,
} from "../../design-system";
import api from "../../services/api";
import { formatBrl } from "../../utils/formatPrice";
import { PriceTablePreview, type SnapshotPayload } from "./PriceTablePreview";

type Template = {
  id: string;
  name: string;
  slug: string;
  content_type?: string;
  config: {
    default_items_per_page?: number;
    min_items_per_page?: number;
    max_items_per_page?: number;
    ui_name?: string;
    columns?: number;
    rows?: number;
    image_fit?: string;
    default_promotion_only?: boolean;
  };
};

type ProductOpt = {
  id: string;
  description: string;
  commercial_description?: string | null;
  unit?: string | null;
  source_product_id?: string;
  regular_price?: number | null;
  promotion_price?: number | null;
};

type Props = {
  open: boolean;
  storeId: string;
  contentId?: string | null;
  onClose: () => void;
  onSaved: () => void;
  /** Filter templates by content_type (default PRICE_TABLE). */
  contentType?: string;
  titleLabel?: string;
};

const STEPS = ["Informações", "Produtos", "Aparência", "Exibição", "Preview"] as const;

export function PriceTableBuilder({
  open,
  storeId,
  contentId,
  onClose,
  onSaved,
  contentType = "PRICE_TABLE",
  titleLabel = "tabela",
}: Props) {
  const [step, setStep] = useState(0);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [mode, setMode] = useState<"MANUAL" | "AUTOMATIC" | "HYBRID">("MANUAL");
  const [templateId, setTemplateId] = useState("");
  const [q, setQ] = useState("");
  const [options, setOptions] = useState<ProductOpt[]>([]);
  const [selected, setSelected] = useState<ProductOpt[]>([]);
  const [pinned, setPinned] = useState<string[]>([]);
  const [excluded, setExcluded] = useState<string[]>([]);
  const [sectionCode, setSectionCode] = useState("");
  const [limitItems, setLimitItems] = useState(16);
  const [sortMode, setSortMode] = useState("NAME_ASC");
  const [promotionOnly, setPromotionOnly] = useState(false);
  const [itemsPerPage, setItemsPerPage] = useState(8);
  const [pageDuration, setPageDuration] = useState(8);
  const [durationMode, setDurationMode] = useState<"FULL_CYCLE" | "FIXED">("FULL_CYCLE");
  const [totalDuration, setTotalDuration] = useState(40);
  const [showUnit, setShowUnit] = useState(true);
  const [title, setTitle] = useState("");
  const [snapshot, setSnapshot] = useState<SnapshotPayload | null>(null);
  const [rulePreviewCount, setRulePreviewCount] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);

  const template = templates.find((t) => t.id === templateId);
  const isVisual =
    contentType === "PRODUCT_GRID" ||
    contentType === "PRODUCT_HERO" ||
    contentType === "PROMOTION_BOARD";
  const lockedPageSize = Boolean(
    isVisual && template?.config?.columns && template?.config?.rows,
  ) || contentType === "PRODUCT_HERO";

  useEffect(() => {
    if (!open || !storeId) return;
    void (async () => {
      const { data } = await api.get<Template[]>("/dynamic-content/templates", {
        params: { store_id: storeId, content_type: contentType },
      });
      setTemplates(data);
      if (!contentId && data[0]) {
        setTemplateId(data[0].id);
        setItemsPerPage(data[0].config.default_items_per_page || 8);
        if (contentType === "PROMOTION_BOARD" || data[0].config.default_promotion_only) {
          setPromotionOnly(true);
        }
      }
      if (contentId) {
        const detail = await api.get(`/dynamic-content/${contentId}`, { params: { store_id: storeId } });
        const d = detail.data;
        setName(d.name || "");
        setDescription(d.description || "");
        setMode(d.selection_mode);
        setTemplateId(d.template_id);
        setTitle(d.config?.title || d.name || "");
        setItemsPerPage(d.config?.items_per_page || 8);
        setPageDuration(d.config?.page_duration_seconds || 8);
        setDurationMode(d.config?.duration_mode || "FULL_CYCLE");
        setTotalDuration(d.config?.total_duration_seconds || 40);
        setShowUnit(d.config?.show_unit !== false);
        if (d.rule) {
          setSectionCode(d.rule.section_code || "");
          setLimitItems(d.rule.limit_items || 16);
          setSortMode(d.rule.sort_mode || "NAME_ASC");
          setPromotionOnly(Boolean(d.rule.promotion_only));
        }
      }
    })();
  }, [open, storeId, contentId, contentType]);

  useEffect(() => {
    if (!open || !storeId || step !== 1) return;
    const t = setTimeout(() => {
      void (async () => {
        const { data } = await api.get<ProductOpt[]>("/retail-products", {
          params: { store_id: storeId, q: q || undefined, limit: 40 },
        });
        setOptions(data);
      })();
    }, 250);
    return () => clearTimeout(t);
  }, [open, storeId, q, step]);

  const pageCountEstimate = useMemo(() => {
    const n = mode === "MANUAL" ? selected.length : limitItems;
    return Math.max(1, Math.ceil(Math.max(n, 1) / Math.max(itemsPerPage, 1)));
  }, [mode, selected.length, limitItems, itemsPerPage]);

  const cycleSeconds =
    durationMode === "FULL_CYCLE" ? pageCountEstimate * pageDuration : totalDuration;

  function toggleSelect(p: ProductOpt) {
    setSelected((cur) => (cur.some((x) => x.id === p.id) ? cur.filter((x) => x.id !== p.id) : [...cur, p]));
  }

  function moveSelected(id: string, dir: -1 | 1) {
    setSelected((cur) => {
      const idx = cur.findIndex((x) => x.id === id);
      if (idx < 0) return cur;
      const j = idx + dir;
      if (j < 0 || j >= cur.length) return cur;
      const next = [...cur];
      [next[idx], next[j]] = [next[j], next[idx]];
      return next;
    });
  }

  function buildBody() {
    const products =
      mode === "MANUAL"
        ? selected.map((p, i) => ({ product_id: p.id, position: i, pinned: false, excluded: false }))
        : mode === "HYBRID"
          ? [
              ...pinned.map((id, i) => ({ product_id: id, position: i, pinned: true, excluded: false })),
              ...excluded.map((id) => ({ product_id: id, pinned: false, excluded: true })),
            ]
          : [];
    return {
      name: name.trim(),
      description: description.trim() || null,
      selection_mode: mode,
      template_id: templateId,
      config: {
        title: title.trim() || name.trim(),
        items_per_page: itemsPerPage,
        page_duration_seconds: pageDuration,
        duration_mode: durationMode,
        total_duration_seconds: totalDuration,
        show_unit: showUnit,
        show_regular_price: true,
        show_promo_badge: true,
        show_image: isVisual ? true : undefined,
        image_fit: template?.config?.image_fit || (isVisual ? "contain" : undefined),
        columns: template?.config?.columns,
        rows: template?.config?.rows,
      },
      rule:
        mode === "MANUAL"
          ? null
          : {
              section_code: sectionCode || null,
              promotion_only: promotionOnly,
              available_only: false,
              limit_items: limitItems,
              sort_mode: sortMode,
            },
      products,
    };
  }

  async function runPreview() {
    setLoadingPreview(true);
    setError(null);
    try {
      const { data } = await api.post<SnapshotPayload>("/dynamic-content/preview", buildBody(), {
        params: { store_id: storeId },
      });
      setSnapshot(data);
      setRulePreviewCount(data.item_count ?? null);
    } catch {
      setError("Não foi possível gerar o preview. Verifique produtos, template e frescor dos preços.");
      setSnapshot(null);
    } finally {
      setLoadingPreview(false);
    }
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const body = buildBody();
      if (contentId) {
        await api.patch(`/dynamic-content/${contentId}`, body, { params: { store_id: storeId } });
        await api.post(`/dynamic-content/${contentId}/resolve`, null, { params: { store_id: storeId } });
      } else {
        const { data } = await api.post("/dynamic-content", body, { params: { store_id: storeId } });
        await api.post(`/dynamic-content/${data.id}/resolve`, null, { params: { store_id: storeId } });
      }
      onSaved();
      onClose();
    } catch {
      setError("Falha ao salvar a tabela.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={contentId ? `Editar ${titleLabel}` : `Nova ${titleLabel}`}
    >
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Etapas">
          {STEPS.map((label, i) => (
            <button
              key={label}
              type="button"
              role="tab"
              aria-selected={step === i}
              className={`rounded-ds px-3 py-1.5 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-600 ${
                step === i ? "bg-brand-800 text-white" : "bg-brand-50 text-brand-900"
              }`}
              onClick={() => setStep(i)}
            >
              {i + 1}. {label}
            </button>
          ))}
        </div>

        {error && (
          <Alert variant="danger" role="alert">
            {error}
          </Alert>
        )}

        {step === 0 && (
          <div className="space-y-3">
            <Input label="Nome" value={name} onChange={(e) => setName(e.target.value)} required />
            <Input
              label="Descrição (opcional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            <Input
              label="Título na TV"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              hint="Se vazio, usa o nome"
            />
          </div>
        )}

        {step === 1 && (
          <div className="space-y-4">
            <fieldset className="space-y-2">
              <legend className="text-sm font-medium text-brand-900">Modo de seleção</legend>
              {(
                [
                  ["MANUAL", "Manual — você escolhe e ordena os produtos"],
                  ["AUTOMATIC", "Automático — regras de seção/grupo"],
                  ["HYBRID", "Híbrido — regras + fixados/excluídos"],
                ] as const
              ).map(([value, label]) => (
                <label key={value} className="flex cursor-pointer items-start gap-2 text-sm">
                  <input
                    type="radio"
                    name="mode"
                    checked={mode === value}
                    onChange={() => setMode(value)}
                    className="mt-1"
                  />
                  <span>{label}</span>
                </label>
              ))}
            </fieldset>

            {(mode === "AUTOMATIC" || mode === "HYBRID") && (
              <div className="grid gap-3 sm:grid-cols-2">
                <Input
                  label="Seção (código)"
                  value={sectionCode}
                  onChange={(e) => setSectionCode(e.target.value)}
                  placeholder="ex.: 1"
                />
                <Input
                  label="Limite de itens"
                  type="number"
                  value={String(limitItems)}
                  onChange={(e) => setLimitItems(Number(e.target.value) || 1)}
                />
                <Select label="Ordenação" value={sortMode} onChange={(e) => setSortMode(e.target.value)}>
                  <option value="NAME_ASC">Nome A–Z</option>
                  <option value="PRICE_ASC">Preço ↑</option>
                  <option value="PRICE_DESC">Preço ↓</option>
                  <option value="PROMOTION_FIRST">Promoções primeiro</option>
                </Select>
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={promotionOnly} onChange={(e) => setPromotionOnly(e.target.checked)} />
                  Somente promoção
                </label>
                <label className="flex items-center gap-2 text-sm text-ink/50">
                  <input type="checkbox" disabled checked={false} readOnly />
                  Somente disponíveis
                  <span className="text-xs">(após validação de estoque)</span>
                </label>
              </div>
            )}

            {(mode === "MANUAL" || mode === "HYBRID") && (
              <>
                <Input label="Buscar produto" value={q} onChange={(e) => setQ(e.target.value)} placeholder="SKU, EAN ou nome" />
                <ul className="max-h-48 space-y-1 overflow-auto rounded-ds border border-brand-100 p-2">
                  {options.map((p) => (
                    <li key={p.id}>
                      <button
                        type="button"
                        className="flex w-full items-center justify-between rounded px-2 py-1.5 text-left text-sm hover:bg-brand-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-600"
                        onClick={() => {
                          if (mode === "MANUAL") toggleSelect(p);
                          else setPinned((c) => (c.includes(p.id) ? c : [...c, p.id]));
                        }}
                      >
                        <span className="truncate">
                          {p.commercial_description || p.description}{" "}
                          <span className="text-ink/50">{p.unit}</span>
                        </span>
                        <span className="tabular-nums text-brand-900">{formatBrl(p.regular_price)}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </>
            )}

            {mode === "MANUAL" && selected.length > 0 && (
              <div>
                <p className="mb-1 text-sm font-medium">Selecionados ({selected.length})</p>
                <ul className="space-y-1">
                  {selected.map((p) => (
                    <li key={p.id} className="flex items-center gap-2 text-sm">
                      <span className="flex-1 truncate">{p.description}</span>
                      <Button size="sm" variant="secondary" onClick={() => moveSelected(p.id, -1)}>
                        ↑
                      </Button>
                      <Button size="sm" variant="secondary" onClick={() => moveSelected(p.id, 1)}>
                        ↓
                      </Button>
                      <Button size="sm" variant="secondary" onClick={() => toggleSelect(p)}>
                        Remover
                      </Button>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {mode === "HYBRID" && (
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <p className="text-sm font-medium">Fixados</p>
                  <p className="text-xs text-ink/60">{pinned.length} produto(s)</p>
                </div>
                <div>
                  <Input
                    label="Excluir product_id"
                    placeholder="colar id e Enter"
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        const v = (e.target as HTMLInputElement).value.trim();
                        if (v) setExcluded((c) => [...c, v]);
                        (e.target as HTMLInputElement).value = "";
                      }
                    }}
                  />
                  <p className="text-xs text-ink/60">{excluded.length} excluído(s)</p>
                </div>
              </div>
            )}

            {(mode === "AUTOMATIC" || mode === "HYBRID") && (
              <Button
                variant="secondary"
                onClick={async () => {
                  await runPreview();
                }}
              >
                Pré-visualizar regra
                {rulePreviewCount != null ? ` (${rulePreviewCount} produtos)` : ""}
              </Button>
            )}
          </div>
        )}

        {step === 2 && (
          <div className="grid gap-3 sm:grid-cols-2">
            {templates.map((t) => (
              <button
                key={t.id}
                type="button"
                aria-pressed={templateId === t.id}
                onClick={() => {
                  setTemplateId(t.id);
                  const geo =
                    t.config.columns && t.config.rows
                      ? t.config.columns * t.config.rows
                      : t.config.default_items_per_page || 8;
                  setItemsPerPage(contentType === "PRODUCT_HERO" ? 1 : geo);
                }}
                className={`rounded-ds border p-3 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-600 ${
                  templateId === t.id ? "border-brand-700 bg-brand-50 ring-2 ring-brand-600" : "border-brand-100"
                }`}
              >
                <div className="mb-2 font-medium text-brand-900">{t.config.ui_name || t.name}</div>
                <div className="rounded bg-slate-900 p-2 text-[10px] leading-tight text-white">
                  <div className="mb-1 font-semibold">HORTIFRUTI</div>
                  <div className="flex justify-between opacity-90">
                    <span>Banana</span>
                    <span>3,99</span>
                  </div>
                  <div className="flex justify-between opacity-90">
                    <span>Melancia</span>
                    <span>4,49</span>
                  </div>
                </div>
              </button>
            ))}
            <label className="flex items-center gap-2 text-sm sm:col-span-2">
              <input type="checkbox" checked={showUnit} onChange={(e) => setShowUnit(e.target.checked)} />
              Mostrar unidade no preço
            </label>
          </div>
        )}

        {step === 3 && (
          <div className="grid gap-3 sm:grid-cols-2">
            <Input
              label="Itens por página"
              type="number"
              value={String(itemsPerPage)}
              onChange={(e) => setItemsPerPage(Number(e.target.value) || 1)}
              disabled={lockedPageSize}
              hint={
                lockedPageSize
                  ? contentType === "PRODUCT_HERO"
                    ? "Hero: 1 produto por página"
                    : `Grade: ${template?.config?.columns}×${template?.config?.rows}`
                  : template
                    ? `${template.config.min_items_per_page}–${template.config.max_items_per_page}`
                    : undefined
              }
            />
            <Input
              label="Tempo por página (s)"
              type="number"
              value={String(pageDuration)}
              onChange={(e) => setPageDuration(Number(e.target.value) || 3)}
              hint="3–120"
            />
            <Select
              label="Modo de duração"
              value={durationMode}
              onChange={(e) => setDurationMode(e.target.value as "FULL_CYCLE" | "FIXED")}
            >
              <option value="FULL_CYCLE">Ciclo completo</option>
              <option value="FIXED">Duração fixa</option>
            </Select>
            {durationMode === "FIXED" && (
              <Input
                label="Duração total (s)"
                type="number"
                value={String(totalDuration)}
                onChange={(e) => setTotalDuration(Number(e.target.value) || 3)}
              />
            )}
            <Alert variant="info" className="sm:col-span-2">
              Estimativa: ~{pageCountEstimate} página(s) · duração do ciclo {cycleSeconds}s
            </Alert>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-3">
            <div className="flex gap-2">
              <Button onClick={() => void runPreview()} disabled={loadingPreview}>
                {loadingPreview ? "Gerando…" : "Gerar preview"}
              </Button>
              {snapshot?.status && <Badge tone={snapshot.status === "PRONTA" ? "success" : "warning"}>{snapshot.status}</Badge>}
            </div>
            {snapshot?.warnings?.map((w) => (
              <Alert key={w} variant="warning" role="alert">
                {w}
              </Alert>
            ))}
            <PriceTablePreview snapshot={snapshot} />
          </div>
        )}

        <div className="flex flex-wrap justify-between gap-2 border-t border-brand-100 pt-3">
          <Button variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <div className="flex gap-2">
            {step > 0 && (
              <Button variant="secondary" onClick={() => setStep((s) => s - 1)}>
                Voltar
              </Button>
            )}
            {step < STEPS.length - 1 ? (
              <Button
                onClick={() => {
                  if (step === 0 && !name.trim()) {
                    setError("Informe o nome da tabela.");
                    return;
                  }
                  setError(null);
                  setStep((s) => s + 1);
                }}
              >
                Continuar
              </Button>
            ) : (
              <Button onClick={() => void save()} disabled={saving || !name.trim() || !templateId}>
                {saving ? "Salvando…" : `Salvar ${titleLabel}`}
              </Button>
            )}
          </div>
        </div>
      </div>
    </Drawer>
  );
}
