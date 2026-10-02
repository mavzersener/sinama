// Veri kaynağı düğümleri: CSV (veri deposu), veritabanı/API ve kolluk kaynakları (demo veri etiketli).
// (executionEngine.ts'den bölündü — Faz 4.)

import { tabloyuGetir, type VeriKaynagi } from '../../lib/veriDeposu';
import { makeResult, makeError, type ExecutionResult } from '../sonuc';

// ---- Source Nodes (Demo Mode: generate sample data when no file uploaded) ----

export async function execCsvSource(nodeId: string, config: Record<string, unknown>, sinyal?: AbortSignal): Promise<ExecutionResult> {
  // Yüklenen dosya: düğüm yalnız kaynağı taşır, tablo veri deposunda (TAMAMI).
  // Depoda yoksa (sayfa yenilendi) sunucudaki kopya aynı ayrıştırıcıyla okunur.
  const kaynak = config._veriKaynagi as VeriKaynagi | undefined;
  if (kaynak) {
    let tablo;
    try {
      tablo = await tabloyuGetir(kaynak, sinyal);
    } catch (e) {
      return makeError(nodeId, 'csv_source', `${kaynak.filename}: ${(e as Error).message}`);
    }
    if (!tablo) {
      return makeError(nodeId, 'csv_source',
        `"${kaynak.filename}" bu oturumda yok: oturum açmadan yüklenen dosya sunucuya kaydedilmez ve sayfa ` +
        'yenilenince kaybolur. Dosyayı yeniden yükleyin (oturum açıkken yüklenen dosya kalıcıdır).');
    }
    const uyarilar: string[] = [];
    if (tablo.rows.length !== kaynak.rowCount) {
      uyarilar.push(`Sunucudaki kopya ${tablo.rows.length} satır; yüklemede ${kaynak.rowCount} satır görülmüştü.`);
    }
    if (kaynak.eskiKesikOlabilir) {
      uyarilar.push('Eski kayıttan taşındı ve tam 5000 satır: eski sürüm büyük dosyaların yalnız ilk 5000 satırını okuyordu — dosyayı yeniden yükleyin.');
    }
    return makeResult(nodeId, 'csv_source', {
      rows: tablo.rows,
      columns: tablo.columns,
      filename: tablo.filename,
      _demoMode: false,
      ...(uyarilar.length ? { uyarilar } : {}),
    }, tablo.rows.length, tablo.columns, tablo.rows.slice(0, 10));
  }

  // Eski biçim (satırlar config içinde) — yükleme yolları bunu depoya taşır;
  // testler ve taşınmamış bellek içi düğümler için desteklenir.
  const uploaded = config._uploadedData as { rows: Record<string, unknown>[]; columns: string[]; filename: string } | undefined;

  if (uploaded && uploaded.rows.length > 0) {
    return makeResult(nodeId, 'csv_source', {
      rows: uploaded.rows,
      columns: uploaded.columns,
      filename: uploaded.filename,
      _demoMode: false
    }, uploaded.rows.length, uploaded.columns, uploaded.rows.slice(0, 10));
  }

  // DEMO MODE: Generate labeled sample data when no file uploaded
  const filename = config.filename as string;
  const columns = ['id', 'name', 'age', 'income', 'score', 'category', 'city', 'date'];
  const categories = ['A', 'B', 'C', 'D'];
  const cities = ['Beijing', 'Shanghai', 'Shenzhen', 'Guangzhou', 'Hangzhou'];
  const rows = Array.from({ length: 200 }, (_, i) => ({
    id: i + 1,
    name: `Person_${i + 1}`,
    age: Math.floor(Math.random() * 50) + 18,
    income: Math.floor(Math.random() * 80000) + 20000,
    score: Number((Math.random() * 100).toFixed(2)),
    category: categories[Math.floor(Math.random() * categories.length)],
    city: cities[Math.floor(Math.random() * cities.length)],
    date: new Date(2024, Math.floor(Math.random() * 12), Math.floor(Math.random() * 28) + 1).toISOString().split('T')[0]
  }));
  return makeResult(nodeId, 'csv_source', { rows, columns, filename, _demoMode: true }, 200, columns, rows.slice(0, 10));
}

export function execDbSource(nodeId: string, config: Record<string, unknown>): ExecutionResult {
  const table = config.table as string;
  const columns = ['user_id', 'username', 'login_time', 'ip_address', 'action', 'status', 'duration'];
  const actions = ['login', 'logout', 'view', 'edit', 'delete', 'download'];
  const statuses = ['success', 'failed', 'timeout'];
  const rows = Array.from({ length: 150 }, (_, i) => ({
    user_id: i + 1,
    username: `user_${String(Math.floor(Math.random() * 1000)).padStart(4, '0')}`,
    login_time: new Date(2025, Math.floor(Math.random() * 12), Math.floor(Math.random() * 28) + 1, Math.floor(Math.random() * 24), Math.floor(Math.random() * 60)).toISOString(),
    ip_address: `10.${Math.floor(Math.random() * 256)}.${Math.floor(Math.random() * 256)}.${Math.floor(Math.random() * 256)}`,
    action: actions[Math.floor(Math.random() * actions.length)],
    status: statuses[Math.floor(Math.random() * statuses.length)],
    duration: Math.floor(Math.random() * 3600)
  }));
  return makeResult(nodeId, 'db_source', { rows, columns, table, query: config.query, _demoMode: true }, 150, columns, rows.slice(0, 10));
}

export function execApiSource(nodeId: string, config: Record<string, unknown>): ExecutionResult {
  const columns = ['timestamp', 'event_type', 'user_id', 'page', 'response_ms', 'device'];
  const events = ['pageview', 'click', 'purchase', 'login', 'search', 'share'];
  const devices = ['desktop', 'mobile', 'tablet'];
  const rows = Array.from({ length: 100 }, (_, i) => ({
    timestamp: new Date(Date.now() - i * 60000).toISOString(),
    event_type: events[Math.floor(Math.random() * events.length)],
    user_id: Math.floor(Math.random() * 500) + 1,
    page: `/page_${Math.floor(Math.random() * 20) + 1}`,
    response_ms: Math.floor(Math.random() * 500) + 50,
    device: devices[Math.floor(Math.random() * devices.length)]
  }));
  return makeResult(nodeId, 'api_source', { rows, columns, url: config.url, _demoMode: true }, 100, columns, rows.slice(0, 10));
}

// ============================================================
// KOLLUK DATA SOURCE NODES (Police-Specific)
// All generate labeled Turkish police demo data
// ============================================================

export function execPtsSource(nodeId: string, config: Record<string, unknown>): ExecutionResult {
  const queryType = config.queryType as string;
  const legalBasis = config.legalBasis as string;
  const kvkkClass = config.kvkkClass as string;

  if (queryType === 'vehicle') {
    const columns = ['person_id', 'tc_kimlik', 'name', 'plate', 'vehicle_type', 'registration_date', 'last_seen', 'violation_count'];
    const rows = Array.from({ length: 80 }, (_, i) => ({
      person_id: `P-${String(i + 1).padStart(5, '0')}`,
      tc_kimlik: String(10000000000 + Math.floor(Math.random() * 899999999)),
      name: ['Ahmet Yilmaz', 'Mehmet Kaya', 'Ali Demir', 'Fatma Sahin', 'Ayse Celik', 'Hasan Aydin', 'Emine Yildiz', 'Mustafa Ozdemir'][Math.floor(Math.random() * 8)],
      plate: `${34 + Math.floor(Math.random() * 80)} ${String.fromCharCode(65 + Math.floor(Math.random() * 26))}${String.fromCharCode(65 + Math.floor(Math.random() * 26))}${String(Math.floor(Math.random() * 900) + 100)}`,
      vehicle_type: ['Otomobil', 'Kamyonet', 'Motosiklet', 'Minibus'][Math.floor(Math.random() * 4)],
      registration_date: new Date(2020 + Math.floor(Math.random() * 6), Math.floor(Math.random() * 12), Math.floor(Math.random() * 28) + 1).toISOString().split('T')[0],
      last_seen: new Date(2026, Math.floor(Math.random() * 6), Math.floor(Math.random() * 28) + 1).toISOString().split('T')[0],
      violation_count: Math.floor(Math.random() * 15)
    }));
    return makeResult(nodeId, 'pts_source', { rows, columns, queryType, legalBasis, kvkkClass, system: 'PTS', _demoMode: true }, 80, columns, rows.slice(0, 10));
  }

  // Person query (default)
  const columns = ['person_id', 'tc_kimlik', 'name_surname', 'birth_date', 'address', 'city', 'criminal_record', 'last_query_date'];
  const cities = ['Istanbul', 'Ankara', 'Izmir', 'Bursa', 'Antalya', 'Adana', 'Gaziantep', 'Konya'];
  const rows = Array.from({ length: 120 }, (_, i) => ({
    person_id: `P-${String(i + 1).padStart(5, '0')}`,
    tc_kimlik: String(10000000000 + Math.floor(Math.random() * 899999999)),
    name_surname: ['Ahmet Yilmaz', 'Mehmet Kaya', 'Ali Demir', 'Fatma Sahin', 'Ayse Celik', 'Hasan Aydin', 'Emine Yildiz', 'Mustafa Ozdemir', 'Zeynep Arslan', 'Ibrahim Tas'][Math.floor(Math.random() * 10)],
    birth_date: new Date(1960 + Math.floor(Math.random() * 45), Math.floor(Math.random() * 12), Math.floor(Math.random() * 28) + 1).toISOString().split('T')[0],
    address: `${['Mah.', 'Cad.', 'Sok.'][Math.floor(Math.random() * 3)]} ${Math.floor(Math.random() * 200) + 1}`,
    city: cities[Math.floor(Math.random() * cities.length)],
    criminal_record: Math.random() > 0.7 ? 'VAR' : 'YOK',
    last_query_date: new Date(2026, Math.floor(Math.random() * 6), Math.floor(Math.random() * 28) + 1).toISOString().split('T')[0]
  }));
  return makeResult(nodeId, 'pts_source', { rows, columns, queryType, legalBasis, kvkkClass, system: 'PTS', _demoMode: true }, 120, columns, rows.slice(0, 10));
}

export function execAnprSource(nodeId: string, config: Record<string, unknown>): ExecutionResult {
  const legalBasis = config.legalBasis as string;
  const kvkkClass = config.kvkkClass as string;
  const columns = ['capture_id', 'plate', 'capture_time', 'location', 'camera_id', 'speed_kmh', 'vehicle_type', 'color', 'direction'];
  const locations = ['Taksim', 'Besiktas', 'Kadikoy', 'Eminonu', 'Levent', 'Mecidiyekoy', 'Sisli', 'Beyoglu', 'Uskudar', 'Aksaray'];
  const rows = Array.from({ length: 200 }, (_, i) => ({
    capture_id: `ANPR-${String(i + 1).padStart(6, '0')}`,
    plate: `${34 + Math.floor(Math.random() * 80)} ${String.fromCharCode(65 + Math.floor(Math.random() * 26))}${String.fromCharCode(65 + Math.floor(Math.random() * 26))}${String(Math.floor(Math.random() * 900) + 100)}`,
    capture_time: new Date(2026, Math.floor(Math.random() * 6), Math.floor(Math.random() * 28) + 1, Math.floor(Math.random() * 24), Math.floor(Math.random() * 60), Math.floor(Math.random() * 60)).toISOString(),
    location: locations[Math.floor(Math.random() * locations.length)],
    camera_id: `CAM-${String(Math.floor(Math.random() * 500) + 1).padStart(4, '0')}`,
    speed_kmh: Math.floor(Math.random() * 120) + 20,
    vehicle_type: ['Otomobil', 'Kamyonet', 'Motosiklet', 'Minibus', 'Otobus', 'TIR'][Math.floor(Math.random() * 6)],
    color: ['Beyaz', 'Siyah', 'Gri', 'Mavi', 'Kirmizi', 'Gumus'][Math.floor(Math.random() * 6)],
    direction: ['Kuzey', 'Guney', 'Dogu', 'Bati'][Math.floor(Math.random() * 4)]
  }));
  return makeResult(nodeId, 'anpr_source', { rows, columns, legalBasis, kvkkClass, system: 'ANPR', _demoMode: true }, 200, columns, rows.slice(0, 10));
}

export function execMobeseSource(nodeId: string, config: Record<string, unknown>): ExecutionResult {
  const legalBasis = config.legalBasis as string;
  const kvkkClass = config.kvkkClass as string;
  const columns = ['camera_id', 'latitude', 'longitude', 'timestamp', 'event_type', 'confidence', 'location_name', 'district'];
  const districts = ['Beyoglu', 'Fatih', 'Kadikoy', 'Besiktas', 'Sisli', 'Uskudar', 'Eminonu', 'Bakirkoy'];
  const events = ['vehicle_pass', 'pedestrian', 'crowd_gathering', 'suspicious_activity', 'traffic_violation', 'loitering'];
  const baseLat = 41.0;
  const baseLng = 28.9;
  const rows = Array.from({ length: 150 }, () => ({
    camera_id: `MBS-${String(Math.floor(Math.random() * 1000) + 1).padStart(4, '0')}`,
    latitude: Number((baseLat + Math.random() * 0.5).toFixed(6)),
    longitude: Number((baseLng + Math.random() * 0.5).toFixed(6)),
    timestamp: new Date(2026, Math.floor(Math.random() * 6), Math.floor(Math.random() * 28) + 1, Math.floor(Math.random() * 24), Math.floor(Math.random() * 60)).toISOString(),
    event_type: events[Math.floor(Math.random() * events.length)],
    confidence: Number((Math.random() * 0.4 + 0.6).toFixed(3)),
    location_name: `Nokta-${Math.floor(Math.random() * 200) + 1}`,
    district: districts[Math.floor(Math.random() * districts.length)]
  }));
  return makeResult(nodeId, 'mobese_source', { rows, columns, legalBasis, kvkkClass, system: 'MOBESE', _demoMode: true }, 150, columns, rows.slice(0, 10));
}

export function execIhbarSource(nodeId: string, config: Record<string, unknown>): ExecutionResult {
  const legalBasis = config.legalBasis as string;
  const kvkkClass = config.kvkkClass as string;
  const columns = ['ihbar_id', 'timestamp', 'category', 'location', 'district', 'reporter_type', 'status', 'response_time_min'];
  const categories = ['gurultu', 'siddet', 'hirsizlik', 'trafik', 'kacakcilik', 'teror', 'intihar', 'kayip'];
  const districts = ['Beyoglu', 'Fatih', 'Kadikoy', 'Besiktas', 'Sisli', 'Uskudar', 'Eminonu', 'Bakirkoy'];
  const rows = Array.from({ length: 180 }, (_, i) => ({
    ihbar_id: `IHB-${String(i + 1).padStart(6, '0')}`,
    timestamp: new Date(2026, Math.floor(Math.random() * 6), Math.floor(Math.random() * 28) + 1, Math.floor(Math.random() * 24), Math.floor(Math.random() * 60)).toISOString(),
    category: categories[Math.floor(Math.random() * categories.length)],
    location: `Cadde-${Math.floor(Math.random() * 300) + 1}`,
    district: districts[Math.floor(Math.random() * districts.length)],
    reporter_type: ['vatandas', 'isyeri', 'belediye', 'diger_kolluk'][Math.floor(Math.random() * 4)],
    status: ['acik', 'kapatildi', 'devam_ediyor'][Math.floor(Math.random() * 3)],
    response_time_min: Math.floor(Math.random() * 45) + 3
  }));
  return makeResult(nodeId, 'ihbar_source', { rows, columns, legalBasis, kvkkClass, system: 'IHBAR', _demoMode: true }, 180, columns, rows.slice(0, 10));
}

export function execAdliSicilSource(nodeId: string, config: Record<string, unknown>): ExecutionResult {
  const tcKimlik = config.tcKimlik as string;
  const legalBasis = config.legalBasis as string;
  const kvkkClass = config.kvkkClass as string;
  const columns = ['record_id', 'tc_kimlik', 'name_surname', 'case_no', 'offense_type', 'verdict', 'court', 'case_date', 'sentence_years'];
  const offenses = ['hirsizlik', 'siddet', 'dolandiricilik', 'uyusturucu', 'silahli_suc', 'trafik', 'mal_varligini_gercek_disinda_bildirme'];
  const courts = ['Istanbul AGY', 'Ankara AGY', 'Izmir AGY', 'Bursa AGY', 'Antalya AGY', 'Adana AGY'];
  const rows = Array.from({ length: 50 }, (_, i) => ({
    record_id: `AS-${String(i + 1).padStart(5, '0')}`,
    tc_kimlik: tcKimlik || String(10000000000 + Math.floor(Math.random() * 899999999)),
    name_surname: ['Ahmet Yilmaz', 'Mehmet Kaya', 'Ali Demir', 'Fatma Sahin', 'Ayse Celik'][Math.floor(Math.random() * 5)],
    case_no: `202${Math.floor(Math.random() * 6)}-${String(Math.floor(Math.random() * 5000) + 1).padStart(4, '0')}`,
    offense_type: offenses[Math.floor(Math.random() * offenses.length)],
    verdict: ['mahkum', 'beraat', 'temyizde', 'kovusturma'][Math.floor(Math.random() * 4)],
    court: courts[Math.floor(Math.random() * courts.length)],
    case_date: new Date(2020 + Math.floor(Math.random() * 6), Math.floor(Math.random() * 12), Math.floor(Math.random() * 28) + 1).toISOString().split('T')[0],
    sentence_years: Math.random() > 0.5 ? Math.floor(Math.random() * 15) + 1 : 0
  }));
  return makeResult(nodeId, 'adli_sicil_source', { rows, columns, tcKimlik, legalBasis, kvkkClass, system: 'ADLI_SICIL', _demoMode: true }, 50, columns, rows.slice(0, 10));
}
