import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useSearchParams } from "react-router-dom";
import api from "../services/api";

export type Store = { id: string; name: string };

const STORAGE_KEY = "real-selected-store";

type StoreContextValue = {
  stores: Store[];
  selectedStoreId: string | null;
  selectedStore: Store | null;
  loading: boolean;
  error: string | null;
  setSelectedStore: (storeId: string, opts?: { syncUrl?: boolean }) => void;
};

const StoreContext = createContext<StoreContextValue | null>(null);

function readStoredId(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [stores, setStores] = useState<Store[]>([]);
  const [selectedStoreId, setSelectedStoreId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const applySelection = useCallback(
    (storeId: string, opts?: { syncUrl?: boolean; replaceUrl?: boolean }) => {
      setSelectedStoreId(storeId);
      try {
        localStorage.setItem(STORAGE_KEY, storeId);
      } catch {
        /* ignore */
      }
      if (opts?.syncUrl) {
        setSearchParams(
          (prev) => {
            const next = new URLSearchParams(prev);
            next.set("store", storeId);
            return next;
          },
          { replace: opts.replaceUrl ?? true },
        );
      }
    },
    [setSearchParams],
  );

  useEffect(() => {
    let alive = true;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const { data } = await api.get<Store[]>("/stores");
        if (!alive) return;
        setStores(data);
        const fromQuery = searchParams.get("store");
        const fromStorage = readStoredId();
        const pick =
          (fromQuery && data.some((s) => s.id === fromQuery) && fromQuery) ||
          (fromStorage && data.some((s) => s.id === fromStorage) && fromStorage) ||
          data[0]?.id ||
          null;
        if (pick) {
          setSelectedStoreId(pick);
          try {
            localStorage.setItem(STORAGE_KEY, pick);
          } catch {
            /* ignore */
          }
          // Deep-link: se URL trouxe ?store=, mantém; senão não polui a URL na carga.
          if (fromQuery && fromQuery !== pick) {
            applySelection(pick, { syncUrl: true, replaceUrl: true });
          }
        }
      } catch {
        if (alive) setError("Não foi possível carregar as lojas.");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- carga inicial do contexto admin
  }, []);

  // Se a URL ganhar ?store= depois (deep-link), sincroniza.
  useEffect(() => {
    const fromQuery = searchParams.get("store");
    if (!fromQuery || !stores.length) return;
    if (!stores.some((s) => s.id === fromQuery)) return;
    if (fromQuery === selectedStoreId) return;
    setSelectedStoreId(fromQuery);
    try {
      localStorage.setItem(STORAGE_KEY, fromQuery);
    } catch {
      /* ignore */
    }
  }, [searchParams, stores, selectedStoreId]);

  const setSelectedStore = useCallback(
    (storeId: string, opts?: { syncUrl?: boolean }) => {
      if (!stores.some((s) => s.id === storeId)) return;
      applySelection(storeId, { syncUrl: opts?.syncUrl ?? true, replaceUrl: false });
    },
    [applySelection, stores],
  );

  const selectedStore = useMemo(
    () => stores.find((s) => s.id === selectedStoreId) || null,
    [stores, selectedStoreId],
  );

  const value = useMemo(
    () => ({
      stores,
      selectedStoreId,
      selectedStore,
      loading,
      error,
      setSelectedStore,
    }),
    [stores, selectedStoreId, selectedStore, loading, error, setSelectedStore],
  );

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStoreContext(): StoreContextValue {
  const ctx = useContext(StoreContext);
  if (!ctx) {
    throw new Error("useStoreContext deve ser usado dentro de StoreProvider");
  }
  return ctx;
}
