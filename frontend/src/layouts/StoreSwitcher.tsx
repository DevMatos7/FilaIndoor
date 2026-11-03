import { Building2 } from "lucide-react";
import { Select } from "../design-system";
import { useStoreContext } from "../context/StoreContext";

export default function StoreSwitcher() {
  const { stores, selectedStoreId, selectedStore, loading, error, setSelectedStore } =
    useStoreContext();

  if (loading) {
    return (
      <div className="flex min-w-[10rem] items-center gap-2 text-sm text-ink/55">
        <Building2 className="h-4 w-4" aria-hidden />
        Carregando lojas…
      </div>
    );
  }

  if (error) {
    return <p className="text-sm text-semantic-danger">{error}</p>;
  }

  if (stores.length === 0) {
    return <p className="text-sm text-ink/55">Nenhuma loja</p>;
  }

  if (stores.length === 1 && selectedStore) {
    return (
      <div className="flex items-center gap-2 text-sm text-ink">
        <Building2 className="h-4 w-4 text-brand-600" aria-hidden />
        <div>
          <p className="text-[10px] uppercase tracking-wide text-ink/45">Loja</p>
          <p className="font-medium text-brand-900">{selectedStore.name}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-w-[12rem]">
      <Select
        label="Loja"
        value={selectedStoreId || ""}
        onChange={(e) => setSelectedStore(e.target.value)}
        aria-label="Selecionar loja"
      >
        {stores.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name}
          </option>
        ))}
      </Select>
    </div>
  );
}
