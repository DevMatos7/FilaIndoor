import { FormEvent, useCallback, useEffect, useState } from "react";
import api from "../services/api";

type Store = { id: string; name: string };
type Playlist = { id: string; name: string };
type Schedule = {
  id: string;
  name: string;
  playlist_id: string;
  playlist_name?: string | null;
  start_date: string | null;
  end_date: string | null;
  start_time: string;
  end_time: string;
  days_of_week: number[];
  priority: string;
  active: boolean;
};
type Channel = {
  id: string;
  store_id: string;
  name: string;
  layout: string;
  default_playlist_id: string | null;
  schedules: Schedule[];
  groups: Array<{ id: string; name: string }>;
};

const DAY_LABELS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

export default function Channels() {
  const [stores, setStores] = useState<Store[]>([]);
  const [storeId, setStoreId] = useState("");
  const [channels, setChannels] = useState<Channel[]>([]);
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [nowInfo, setNowInfo] = useState<{ source?: string; conflicts?: Array<{ message: string }>; schedule?: Schedule | null } | null>(null);
  const [channelName, setChannelName] = useState("");
  const [groupName, setGroupName] = useState("");
  const [schedName, setSchedName] = useState("Agenda comercial");
  const [schedPlaylist, setSchedPlaylist] = useState("");
  const [startTime, setStartTime] = useState("08:00");
  const [endTime, setEndTime] = useState("21:00");
  const [days, setDays] = useState<number[]>([0, 1, 2, 3, 4, 5, 6]);
  const [priority, setPriority] = useState("NORMAL");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const selected = channels.find((c) => c.id === selectedId) || null;

  const load = useCallback(async () => {
    if (!storeId) return;
    setLoading(true);
    setError(null);
    try {
      const [ch, pl] = await Promise.all([
        api.get<Channel[]>("/channels", { params: { store_id: storeId } }),
        api.get<Playlist[]>("/playlists", { params: { store_id: storeId } }),
      ]);
      setChannels(ch.data);
      setPlaylists(pl.data);
      setSelectedId((prev) => (prev && ch.data.some((c) => c.id === prev) ? prev : ch.data[0]?.id || null));
      if (!schedPlaylist && pl.data[0]) setSchedPlaylist(pl.data[0].id);
    } catch {
      setError("Falha ao carregar canais.");
    } finally {
      setLoading(false);
    }
  }, [storeId]);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get<Store[]>("/stores");
        setStores(data);
        setStoreId((prev) => prev || data[0]?.id || "");
      } catch {
        /* ignore */
      }
    })();
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!selectedId) {
      setNowInfo(null);
      return;
    }
    (async () => {
      try {
        const { data } = await api.get(`/channels/${selectedId}/now`);
        setNowInfo(data);
      } catch {
        setNowInfo(null);
      }
    })();
  }, [selectedId, channels]);

  async function createChannel(e: FormEvent) {
    e.preventDefault();
    if (!storeId || !channelName.trim()) return;
    try {
      const { data } = await api.post<Channel>("/channels", {
        store_id: storeId,
        name: channelName.trim(),
        default_playlist_id: playlists[0]?.id || null,
      });
      setChannelName("");
      setMessage(`Canal “${data.name}” criado.`);
      await load();
      setSelectedId(data.id);
    } catch {
      setError("Não foi possível criar o canal.");
    }
  }

  async function createGroup(e: FormEvent) {
    e.preventDefault();
    if (!selectedId || !groupName.trim()) return;
    try {
      await api.post("/screen-groups", { store_id: storeId, channel_id: selectedId, name: groupName.trim() });
      setGroupName("");
      setMessage("Grupo de telas criado.");
      await load();
    } catch {
      setError("Falha ao criar grupo.");
    }
  }

  async function createSchedule(e: FormEvent) {
    e.preventDefault();
    if (!selectedId || !schedPlaylist) return;
    try {
      await api.post("/schedules", {
        channel_id: selectedId,
        playlist_id: schedPlaylist,
        name: schedName,
        start_time: startTime,
        end_time: endTime,
        days_of_week: days,
        priority,
      });
      setMessage("Agenda criada.");
      await load();
    } catch {
      setError("Falha ao criar agenda.");
    }
  }

  async function removeSchedule(id: string) {
    try {
      await api.delete(`/schedules/${id}`);
      await load();
    } catch {
      setError("Falha ao remover agenda.");
    }
  }

  function toggleDay(d: number) {
    setDays((prev) => (prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d].sort()));
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold text-brand-900">Canais & Agenda</h1>
          <p className="mt-1 text-ink/70">Programe playlists por dia/horário com prioridade e detecte conflitos.</p>
        </div>
        <label className="text-sm">
          Loja
          <select className="mt-1 block min-w-[14rem] border border-brand-100 bg-sand px-2 py-2" value={storeId} onChange={(e) => setStoreId(e.target.value)}>
            {stores.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </label>
      </div>

      {error && <p className="border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>}
      {message && <p className="border border-brand-100 bg-brand-50 px-3 py-2 text-sm text-brand-900">{message}</p>}

      <form onSubmit={createChannel} className="flex flex-wrap items-end gap-3 border border-brand-100 bg-white/80 p-4">
        <label className="text-sm">
          Novo canal
          <input className="mt-1 block min-w-[14rem] border border-brand-100 bg-sand px-3 py-2" value={channelName} onChange={(e) => setChannelName(e.target.value)} placeholder="Ex.: Canal Açougue" />
        </label>
        <button type="submit" className="bg-brand-700 px-4 py-2 text-sm font-semibold text-white">Criar canal</button>
      </form>

      {loading && <p className="text-sm text-ink/60">Carregando…</p>}

      {!loading && (
        <div className="grid gap-6 xl:grid-cols-[220px_1.3fr_1fr]">
          <section className="border border-brand-100 bg-white/80 p-3">
            <h2 className="font-display text-lg font-semibold">Canais</h2>
            <ul className="mt-3 space-y-1 text-sm">
              {channels.map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    className={`w-full px-2 py-2 text-left ${selectedId === c.id ? "bg-brand-50 font-semibold" : "hover:bg-brand-50/60"}`}
                    onClick={() => setSelectedId(c.id)}
                  >
                    {c.name}
                  </button>
                </li>
              ))}
              {channels.length === 0 && <li className="text-ink/60">Nenhum canal.</li>}
            </ul>
          </section>

          <section className="space-y-4 border border-brand-100 bg-white/80 p-4">
            {!selected ? (
              <p className="text-sm text-ink/60">Selecione um canal.</p>
            ) : (
              <>
                <div>
                  <h2 className="font-display text-xl font-semibold">{selected.name}</h2>
                  <p className="text-sm text-ink/60">Layout: {selected.layout}</p>
                  {nowInfo && (
                    <div className="mt-2 border border-brand-50 bg-brand-50/50 px-3 py-2 text-sm">
                      <p>
                        Agora: <strong>{nowInfo.source}</strong>
                        {nowInfo.schedule ? ` · ${nowInfo.schedule.name} (${nowInfo.schedule.priority})` : ""}
                      </p>
                      {(nowInfo.conflicts || []).map((c, i) => (
                        <p key={i} className="mt-1 text-amber-800">{c.message}</p>
                      ))}
                    </div>
                  )}
                </div>

                <div>
                  <h3 className="text-sm font-medium">Agendas</h3>
                  <ul className="mt-2 space-y-2 text-sm">
                    {selected.schedules.filter((s) => s.active).map((s) => (
                      <li key={s.id} className="flex flex-wrap items-center justify-between gap-2 border border-brand-50 px-3 py-2">
                        <div>
                          <p className="font-semibold">{s.name} · {s.priority}</p>
                          <p className="text-ink/60">
                            {s.start_time}–{s.end_time} · {s.days_of_week.map((d) => DAY_LABELS[d]).join(" ")} · {s.playlist_name || s.playlist_id}
                          </p>
                        </div>
                        <button type="button" className="text-red-700 underline" onClick={() => void removeSchedule(s.id)}>Remover</button>
                      </li>
                    ))}
                    {selected.schedules.filter((s) => s.active).length === 0 && (
                      <li className="text-ink/60">Sem agendas — usa playlist padrão do canal/display.</li>
                    )}
                  </ul>
                </div>

                <form onSubmit={createSchedule} className="space-y-3 border-t border-brand-50 pt-4">
                  <h3 className="text-sm font-medium">Nova agenda</h3>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <label className="text-sm">
                      Nome
                      <input className="mt-1 w-full border border-brand-100 bg-sand px-2 py-2" value={schedName} onChange={(e) => setSchedName(e.target.value)} />
                    </label>
                    <label className="text-sm">
                      Playlist
                      <select className="mt-1 w-full border border-brand-100 bg-sand px-2 py-2" value={schedPlaylist} onChange={(e) => setSchedPlaylist(e.target.value)}>
                        {playlists.map((p) => (
                          <option key={p.id} value={p.id}>{p.name}</option>
                        ))}
                      </select>
                    </label>
                    <label className="text-sm">
                      Início
                      <input type="time" className="mt-1 w-full border border-brand-100 bg-sand px-2 py-2" value={startTime} onChange={(e) => setStartTime(e.target.value)} />
                    </label>
                    <label className="text-sm">
                      Fim
                      <input type="time" className="mt-1 w-full border border-brand-100 bg-sand px-2 py-2" value={endTime} onChange={(e) => setEndTime(e.target.value)} />
                    </label>
                    <label className="text-sm sm:col-span-2">
                      Prioridade
                      <select className="mt-1 w-full border border-brand-100 bg-sand px-2 py-2" value={priority} onChange={(e) => setPriority(e.target.value)}>
                        <option value="NORMAL">NORMAL</option>
                        <option value="HIGH">HIGH</option>
                        <option value="EMERGENCY">EMERGENCY</option>
                      </select>
                    </label>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {DAY_LABELS.map((label, idx) => (
                      <button
                        key={label}
                        type="button"
                        onClick={() => toggleDay(idx)}
                        className={`px-2 py-1 text-xs ${days.includes(idx) ? "bg-brand-700 text-white" : "border border-brand-100 text-ink/70"}`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  <button type="submit" className="bg-brand-700 px-4 py-2 text-sm font-semibold text-white">Adicionar agenda</button>
                </form>
              </>
            )}
          </section>

          <section className="border border-brand-100 bg-white/80 p-4">
            <h2 className="font-display text-xl font-semibold">Grupos de tela</h2>
            {!selected ? (
              <p className="mt-3 text-sm text-ink/60">Selecione um canal.</p>
            ) : (
              <>
                <ul className="mt-3 space-y-1 text-sm">
                  {selected.groups.map((g) => (
                    <li key={g.id} className="border-b border-brand-50 py-2">{g.name}</li>
                  ))}
                  {selected.groups.length === 0 && <li className="text-ink/60">Nenhum grupo.</li>}
                </ul>
                <form onSubmit={createGroup} className="mt-4 space-y-2">
                  <input className="w-full border border-brand-100 bg-sand px-2 py-2 text-sm" value={groupName} onChange={(e) => setGroupName(e.target.value)} placeholder="Nome do grupo" />
                  <button type="submit" className="border border-brand-700 px-3 py-2 text-sm font-semibold text-brand-700">Criar grupo</button>
                </form>
                <p className="mt-4 text-xs text-ink/50">
                  Associe TVs ao canal em Dispositivos (campo channel). Prioridade: EMERGENCY &gt; HIGH &gt; NORMAL. Chamada de senha sempre sobrepõe a mídia.
                </p>
              </>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
