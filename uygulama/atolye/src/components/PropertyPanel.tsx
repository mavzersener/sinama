import { useCallback, useMemo, useRef, useState } from 'react';
import { useStore } from '../store/useStore';
import { dosyayiCoz, kaynakOlustur, veriAl, veriKaydet, type VeriKaynagi } from '../lib/veriDeposu';
import { useDatasetUpload } from '../hooks/useDatasetUpload';
import AnalysisSuggestions from './AnalysisSuggestions';
import { getNodeDefinition, type ConfigField } from '../nodes/nodeDefinitions';
import { ustSutunlariBul, sutunlariSirala } from '../lib/ustSutunlar';
import { nodeLabel, nodeDesc } from '../i18nNodes';
import {
  MousePointer, CheckCircle2, Table2, FileSpreadsheet, Database, Globe,
  Filter, PlusCircle, BarChart3, ArrowUpDown, GitMerge, CopyMinus,
  PieChart, TrendingUp, Link2, Target, AlertTriangle, Grid3X3,
  BarChart, Download, Bell, Box, Upload, FileCheck, Crosshair, ShieldCheck, Shuffle,
  Shield, Camera, Video, PhoneCall, Scale, Network, MapPin, Clock, Users, FileLock, Bot, Wand2
} from 'lucide-react';

const iconComponents: Record<string, React.ComponentType<{ size?: number; color?: string; className?: string }>> = {
  FileSpreadsheet, Database, Globe, Filter, PlusCircle,
  BarChart3, ArrowUpDown, Merge: GitMerge, CopyMinus, PieChart,
  TrendingUp, Link2, Target, AlertTriangle, Grid3X3,
  BarChart, Download, Bell, Box, Crosshair, ShieldCheck, Shuffle,
  Shield, Camera, Video, PhoneCall, Scale, Network, MapPin, Clock, Users, FileLock, Bot, Wand2
};

interface ConfigFieldInputProps {
  field: ConfigField;
  value: unknown;
  onChange: (v: unknown) => void;
  /** Yukarı akıştan okunan sütun adları ('column' alanları için). */
  ustSutunlar?: string[];
}

function ConfigFieldInput({ field, value, onChange, ustSutunlar = [] }: ConfigFieldInputProps) {
  const inputClasses = "w-full px-2.5 py-1.5 text-xs bg-slate-800 border border-slate-700 rounded-lg text-slate-300 placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors";

  switch (field.type) {
    // Sütun seçici: kullanıcı adı TAHMİN ETMEZ, listeden seçer.
    // Yukarı akışta henüz veri yoksa serbest metne düşer — kullanıcı
    // veriyi yüklemeden önce de alanı doldurabilsin.
    case 'column': {
      if (ustSutunlar.length === 0) {
        return (
          <div className="space-y-1">
            <input
              type="text"
              value={(value as string) || ''}
              onChange={(e) => onChange(e.target.value)}
              placeholder={field.placeholder}
              className={inputClasses}
            />
            <div className="text-[10px] text-slate-500">
              Veri yüklendikten sonra burada sütun listesi çıkar.
            </div>
          </div>
        );
      }
      const secenekler = sutunlariSirala(ustSutunlar, field.sutunIpucu ?? null);
      const mevcut = (value as string) || '';
      // Kayıtlı değer listede yoksa (veri değişmiş olabilir) görünür kalsın.
      const listede = mevcut === '' || secenekler.includes(mevcut);
      return (
        <div className="space-y-1">
          <select
            value={listede ? mevcut : ''}
            onChange={(e) => onChange(e.target.value)}
            className={inputClasses}
          >
            <option value="">{field.required ? '— seçiniz —' : '— yok —'}</option>
            {secenekler.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          {!listede && (
            <div className="text-[10px] text-amber-400">
              Kayıtlı değer &quot;{mevcut}&quot; veride yok; yeniden seçin.
            </div>
          )}
        </div>
      );
    }
    case 'text':
      return (
        <input type="text" value={(value as string) || ''} onChange={(e) => onChange(e.target.value)} placeholder={field.placeholder} className={inputClasses} />
      );
    case 'number':
      return (
        // Boş alan NaN değil undefined yazar (= varsayılanı kullan): NaN, "?? varsayılan"
        // denetiminden geçip JSON'da null olarak ML servisine gidiyordu.
        <input type="number" value={value !== undefined ? Number(value) : Number(field.default ?? 0)} onChange={(e) => { const n = parseFloat(e.target.value); onChange(Number.isNaN(n) ? undefined : n); }} placeholder={field.placeholder} step={0.01} className={inputClasses} />
      );
    case 'textarea':
      return (
        <textarea value={(value as string) || ''} onChange={(e) => onChange(e.target.value)} placeholder={field.placeholder} rows={3} className={`${inputClasses} resize-none`} />
      );
    case 'select':
      return (
        <select value={(value as string) || (field.default as string) || ''} onChange={(e) => onChange(e.target.value)} className={inputClasses}>
          {field.options?.map((opt) => <option key={opt} value={opt}>{opt}</option>)}
        </select>
      );
    case 'multiselect':
      return (
        <div className="flex flex-wrap gap-1.5">
          {field.options?.map((opt) => {
            const selected = ((value as string[]) || []).includes(opt);
            return (
              <button key={opt} onClick={() => { const c = (value as string[]) || []; onChange(selected ? c.filter((v) => v !== opt) : [...c, opt]); }}
                className={`px-2 py-1 text-[10px] rounded-md border transition-all ${selected ? 'bg-blue-600/20 border-blue-500/50 text-blue-400' : 'bg-slate-800 border-slate-700 text-slate-500 hover:border-slate-600'}`}>
                {opt}
              </button>
            );
          })}
        </div>
      );
    case 'boolean': {
      // Tanımsız değer alanın varsayılanını gösterir: varsayılanı true olan
      // alan (ör. standardize) eskiden kapalı görünüp motorda açık çalışıyordu.
      const acik = value === undefined ? Boolean(field.default) : Boolean(value);
      return (
        <button onClick={() => onChange(!acik)} className={`w-10 h-5 rounded-full relative transition-colors ${acik ? 'bg-blue-600' : 'bg-slate-700'}`}>
          <div className={`w-4 h-4 bg-white rounded-full absolute top-0.5 transition-transform ${acik ? 'translate-x-5' : 'translate-x-0.5'}`} />
        </button>
      );
    }
    default:
      return <input type="text" value={(value as string) || ''} onChange={(e) => onChange(e.target.value)} className={inputClasses} />;
  }
}

function CsvUploadSection({ nodeId, config, onConfigChange }: { nodeId: string; config: Record<string, unknown>; onConfigChange: (c: Record<string, unknown>) => void }) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { upload, status: uploadStatus } = useDatasetUpload();
  const [okuma, setOkuma] = useState<{ durum: 'bos' | 'suruyor' | 'hata'; ileti?: string }>({ durum: 'bos' });
  const kaynak = config._veriKaynagi as VeriKaynagi | undefined;
  const bellekte = kaynak ? !!veriAl(kaynak.anahtar) : false;

  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = ''; // aynı dosya yeniden seçilebilsin
    if (!file) return;
    const secenek = { hasHeader: config.hasHeader !== false, delimiter: (config.delimiter as string) || ',' };

    // Dosyanın TAMAMI okunur (eskiden yalnız ilk 5000 satır — preview: 5000).
    setOkuma({ durum: 'suruyor' });
    let tablo;
    try {
      tablo = await dosyayiCoz(file, secenek);
    } catch (err) {
      setOkuma({ durum: 'hata', ileti: `CSV okunamadı: ${(err as Error).message}` });
      return;
    }
    setOkuma({ durum: 'bos' });

    // Önce bu oturumda kullanılabilir; düğüm yalnız kaynağı (önizleme dahil) taşır.
    const yerel = `yerel:${crypto.randomUUID()}`;
    veriKaydet(yerel, tablo);
    onConfigChange({
      filename: file.name,
      _veriKaynagi: kaynakOlustur(yerel, tablo, secenek),
      _uploadedData: undefined,
      _datasetId: undefined,
      _demoMode: false,
    });

    // Sunucuya kalıcı kopya (oturum varsa). Bu arada dosya değiştirildiyse
    // geç gelen yanıt yeni dosyanın üzerine YAZILMAZ.
    const sonuc = await upload(file, { name: file.name, ...secenek });
    const guncel = useStore.getState().nodes.find((n) => n.id === nodeId)?.data.config?._veriKaynagi as VeriKaynagi | undefined;
    if (!sonuc || guncel?.anahtar !== yerel) return;
    const ds = `ds:${sonuc.id}`;
    veriKaydet(ds, tablo);
    onConfigChange({ _veriKaynagi: { ...guncel, anahtar: ds, datasetId: sonuc.id } });
  }, [config.hasHeader, config.delimiter, nodeId, onConfigChange, upload]);

  const konum = (() => {
    if (!kaynak) return null;
    if (uploadStatus === 'uploading') return <span className="text-blue-400">Sunucuya yükleniyor…</span>;
    if (kaynak.datasetId !== undefined) {
      return <span className="text-emerald-400">☁ Sunucuda kayıtlı (#{kaynak.datasetId}){bellekte ? '' : ' — koşuda sunucudan yüklenecek'}</span>;
    }
    if (!bellekte) return <span className="text-red-400">Bu oturumda yok — dosyayı yeniden yükleyin.</span>;
    if (uploadStatus === 'error') return <span className="text-red-400">Sunucuya yüklenemedi: yalnız bu oturumda, sayfa yenilenince kaybolur.</span>;
    return <span className="text-amber-400">Yalnız bu oturumda (oturum yok): sayfa yenilenince kaybolur.</span>;
  })();

  return (
    <div className="mt-3 p-3 rounded-lg bg-slate-800/50 border border-slate-700 space-y-2">
      <div className="flex items-center gap-2 text-xs text-slate-400">
        <Upload size={14} />
        <span className="font-medium">CSV File Upload</span>
      </div>

      <input ref={fileInputRef} type="file" accept=".csv,.txt" onChange={handleFileSelect} className="hidden" />

      {okuma.durum === 'suruyor' && <div className="text-[10px] text-blue-400">Dosya okunuyor…</div>}
      {okuma.durum === 'hata' && <div className="text-[10px] text-red-400">{okuma.ileti}</div>}

      {kaynak ? (
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 text-[10px] text-emerald-400">
            <FileCheck size={12} />
            <span className="font-medium">{kaynak.filename}</span>
          </div>
          <div className="text-[10px] text-slate-500">
            {kaynak.rowCount.toLocaleString()} rows | {kaynak.columns.length} columns
          </div>
          <div className="text-[10px] text-slate-600 truncate">
            Columns: {kaynak.columns.join(', ')}
          </div>
          <div className="text-[10px]">{konum}</div>
          {kaynak.eskiKesikOlabilir && (
            <div className="text-[10px] text-amber-400">
              Eski kayıt: tam 5000 satır — eski sürüm büyük dosyaların yalnız ilk 5000 satırını okuyordu. Dosyayı yeniden yükleyin.
            </div>
          )}
          <button
            onClick={() => fileInputRef.current?.click()}
            className="text-[10px] text-blue-400 hover:text-blue-300 transition-colors"
          >
            Replace file...
          </button>
        </div>
      ) : (
        <button
          onClick={() => fileInputRef.current?.click()}
          className="w-full py-2 text-[10px] text-slate-400 border border-dashed border-slate-700 rounded-lg hover:border-blue-500 hover:text-blue-400 transition-all"
        >
          Click to upload CSV file
        </button>
      )}
    </div>
  );
}

export default function PropertyPanel() {
  const nodes = useStore((s) => s.nodes);
  const selectedNode = useStore((s) => s.selectedNode);
  const updateNodeConfig = useStore((s) => s.updateNodeConfig);
  const setDataPreviewNodeId = useStore((s) => s.setDataPreviewNodeId);

  const language = useStore((s) => s.language);
  const edges = useStore((s) => s.edges);
  const node = nodes.find((n) => n.id === selectedNode);

  // 'column' alanlarını beslemek için sütun adları: önce düğümün KENDİ
  // verisi (csv_source seçiliyse), yoksa yukarı akıştaki en yakın kaynak.
  // Böylece kullanıcı sütun adını tahmin etmek zorunda kalmaz.
  const ustSutunlar = useMemo(() => {
    if (!node) return [];
    const ozetler = nodes.map((n) => ({
      id: n.id,
      sonucSutunlari: n.data.result?.columns,
      yuklenenSutunlar: (n.data.config?._veriKaynagi as VeriKaynagi | undefined)?.columns,
    }));
    const kendi = ozetler.find((o) => o.id === node.id);
    const kendiSutun = kendi?.sonucSutunlari?.length ? kendi.sonucSutunlari : kendi?.yuklenenSutunlar;
    if (kendiSutun?.length) return [...kendiSutun];
    return ustSutunlariBul(node.id, ozetler, edges);
  }, [node, nodes, edges]);
  const definition = node ? getNodeDefinition(node.data.type) : null;

  if (!node || !definition) {
    return (
      <div className="w-[280px] bg-slate-900 border-l border-slate-800 flex flex-col">
        <div className="px-4 py-3 border-b border-slate-800">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Properties</h3>
        </div>
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center">
            <MousePointer size={32} className="mx-auto text-slate-600 mb-3" />
            <p className="text-xs text-slate-500">Select a node to configure its properties</p>
            <div className="mt-3 text-[10px] text-slate-600 space-y-1">
              <p>Ctrl+Z to undo</p>
              <p>Ctrl+Shift+Z to redo</p>
              <p>Delete to remove selected node</p>
              <p>D to view data preview</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const IconComponent = iconComponents[definition.icon] || Box;
  const status = node.data.status || 'idle';
  const hasResult = !!node.data.result;
  const uploadedData = node.data.config?._veriKaynagi as VeriKaynagi | undefined;

  return (
    <div className="w-[280px] bg-slate-900 border-l border-slate-800 flex flex-col">
      <div className="px-4 py-3 border-b border-slate-800">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Properties</h3>
      </div>

      <div className="px-4 py-3 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ backgroundColor: definition.color + '25' }}>
            <IconComponent size={18} color={definition.color} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold text-white truncate">{nodeLabel(language, node.data.type, node.data.label)}</div>
            <div className="text-[10px] text-slate-500">{nodeDesc(language, node.data.type, definition.description)}</div>
          </div>
        </div>
        <div className="flex items-center gap-2 mt-2">
          <span className="text-[10px] bg-slate-800 text-slate-500 px-2 py-0.5 rounded">ID: {node.id.slice(-6)}</span>
          {uploadedData && (
            <span className="text-[10px] bg-emerald-900/30 text-emerald-400 px-2 py-0.5 rounded">
              Real Data
            </span>
          )}
          {!uploadedData && (node.data.type === 'csv_source' || node.data.type === 'db_source' || node.data.type === 'api_source') && (
            <span className="text-[10px] bg-amber-900/30 text-amber-400 px-2 py-0.5 rounded">
              Demo Mode
            </span>
          )}
          {/* KVKK Classification Badge for police data sources */}
          {node.data.config?.kvkkClass ? (
            <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
              node.data.config.kvkkClass === 'Cok Gizli' ? 'bg-red-900/50 text-red-400 border border-red-800/50' :
              node.data.config.kvkkClass === 'Gizli' ? 'bg-orange-900/50 text-orange-400 border border-orange-800/50' :
              'bg-amber-900/50 text-amber-400 border border-amber-800/50'
            }`}>
              {String(node.data.config.kvkkClass)}
            </span>
          ) : null}
          {/* Legal Basis Badge for police data sources */}
          {node.data.config?.legalBasis ? (
            <span className="text-[10px] bg-slate-800 text-slate-500 px-2 py-0.5 rounded">
              {String(node.data.config.legalBasis)}
            </span>
          ) : null}
          {status !== 'idle' && (
            <span className={`text-[10px] px-2 py-0.5 rounded capitalize ${status === 'running' ? 'bg-blue-900/50 text-blue-400' : status === 'completed' ? 'bg-emerald-900/50 text-emerald-400' : 'bg-red-900/50 text-red-400'}`}>{status}</span>
          )}
          {hasResult && (
            <button onClick={() => setDataPreviewNodeId(node.id)} className="flex items-center gap-1 text-[10px] text-blue-400 hover:text-blue-300 transition-colors">
              <Table2 size={10} /> Preview
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* CSV Upload for csv_source nodes (P0-1) */}
        {node.data.type === 'csv_source' && (
          <CsvUploadSection
            nodeId={node.id}
            config={node.data.config}
            onConfigChange={(c) => updateNodeConfig(node.id, c)}
          />
        )}

        {definition.configFields.map((field) => (
          <div key={field.name}>
            <label className="flex items-center gap-1 text-xs text-slate-400 mb-1.5">
              {field.label}
              {field.required && <span className="text-red-400">*</span>}
            </label>
            <ConfigFieldInput
              field={field}
              value={node.data.config?.[field.name]}
              onChange={(v) => updateNodeConfig(node.id, { [field.name]: v })}
              ustSutunlar={ustSutunlar}
            />
          </div>
        ))}

        {/* Data-driven analysis recommendations */}
        {(definition.category === 'Data Input' ||
          definition.category === 'Kolluk Data' ||
          node.data.config?._veriKaynagi ||
          node.data.result) && <AnalysisSuggestions node={node} />}

        {node.data.result && node.data.result.status === 'success' && (
          <div className="mt-4 pt-4 border-t border-slate-800">
            <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-medium mb-2">
              <CheckCircle2 size={14} /> Execution Result
            </div>
            <div className="text-[10px] text-slate-500 space-y-1">
              {node.data.result.rowCount !== undefined && <div className="flex justify-between"><span>Rows:</span><span className="text-slate-300">{node.data.result.rowCount.toLocaleString()}</span></div>}
              {node.data.result.columns && <div className="flex justify-between"><span>Columns:</span><span className="text-slate-300">{node.data.result.columns.length}</span></div>}
            </div>
            {typeof node.data.result.data?.insight === 'string' && (
              <div className="mt-2 p-2 rounded-lg bg-cyan-950/30 border border-cyan-800/40 text-[11px] text-cyan-100 whitespace-pre-wrap leading-snug">
                {String(node.data.result.data.insight)}
              </div>
            )}
          </div>
        )}

        {node.data.result && node.data.result.status === 'error' && (
          <div className="mt-4 pt-4 border-t border-slate-800">
            <div className="flex items-center gap-1.5 text-xs text-red-400 font-medium mb-2">
              <AlertTriangle size={14} /> Execution Error
            </div>
            <p className="text-[10px] text-red-400/80">{node.data.result.error}</p>
          </div>
        )}
      </div>
    </div>
  );
}
