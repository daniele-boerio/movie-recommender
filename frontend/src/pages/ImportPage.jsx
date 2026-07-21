import { useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, CheckCircle2, X, Download } from 'lucide-react';
import { api } from '../api';
import { useApp } from '../App';

const BATCH = 20;

// Parser CSV minimale: gestisce i campi tra virgolette con virgole ed escape ("").
// Assume una riga per record (niente a-capo dentro i campi: raro nei CSV di film).
function parseCSV(text) {
  const lines = text.replace(/\r\n?/g, '\n').split('\n').filter((l) => l.length);
  if (!lines.length) return [];
  const parseLine = (line) => {
    const out = [];
    let cur = '';
    let inQ = false;
    for (let i = 0; i < line.length; i++) {
      const c = line[i];
      if (inQ) {
        if (c === '"') {
          if (line[i + 1] === '"') { cur += '"'; i++; } else inQ = false;
        } else cur += c;
      } else if (c === '"') inQ = true;
      else if (c === ',') { out.push(cur); cur = ''; }
      else cur += c;
    }
    out.push(cur);
    return out;
  };
  const headers = parseLine(lines[0]).map((h) => h.trim().toLowerCase());
  return lines.slice(1).map((line) => {
    const cells = parseLine(line);
    const obj = {};
    headers.forEach((h, i) => { obj[h] = (cells[i] ?? '').trim(); });
    return obj;
  });
}

// Colonne flessibili: Letterboxd (Name/Year/Rating), IMDb (Title/Year/Title Type/
// Your Rating) o un CSV generico (title/year/type/rating).
function mapRows(objs) {
  return objs
    .map((o) => {
      const title = o.title || o.name || o['original title'] || '';
      const year = parseInt(o.year, 10) || null;
      // IMDb usa "Title Type" con valori come tvSeries/tvMiniSeries: il match su "tv"
      // (o "serie"/"mini") li cattura tutti; tutto il resto resta "movie".
      const t = (o.type || o.media_type || o['title type'] || 'movie').toLowerCase();
      const media_type = /tv|serie|series|show|mini/.test(t) ? 'tv' : 'movie';
      // IMDb chiama la colonna "Your Rating" (scala 1-10), Letterboxd "Rating" (su 5).
      const raw = String(o.rating || o['your rating'] || '').replace(',', '.');
      const r = parseFloat(raw);
      return { title, year, media_type, ratingRaw: Number.isFinite(r) ? r : null };
    })
    .filter((r) => r.title);
}

export default function ImportPage() {
  const { reloadLists, addToast } = useApp();
  const navigate = useNavigate();
  const inputRef = useRef(null);

  const [fileName, setFileName] = useState('');
  const [rows, setRows] = useState([]);
  const [scale, setScale] = useState('auto'); // 'auto' | '5' | '10'
  const [parseError, setParseError] = useState('');
  const [dragOver, setDragOver] = useState(false);

  const [importing, setImporting] = useState(false);
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const [report, setReport] = useState(null);
  const [exporting, setExporting] = useState(false);

  const detectedScale = useMemo(() => {
    const rr = rows.map((r) => r.ratingRaw).filter((r) => r != null);
    return rr.length && Math.max(...rr) <= 5 ? 5 : 10;
  }, [rows]);
  const effectiveScale = scale === 'auto' ? detectedScale : +scale;

  const handleFile = (file) => {
    setParseError('');
    setReport(null);
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const mapped = mapRows(parseCSV(String(reader.result)));
        if (!mapped.length) setParseError('Nessuna riga valida trovata (serve una colonna "title" o "name").');
        setRows(mapped);
      } catch {
        setParseError('Impossibile leggere il file CSV.');
        setRows([]);
      }
    };
    reader.readAsText(file);
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  };

  const normalizeRating = (raw) => {
    if (raw == null) return null;
    const v = effectiveScale === 5 ? raw * 2 : raw;
    return Math.min(10, Math.max(1, Math.round(v)));
  };

  const startImport = async () => {
    setImporting(true);
    setReport(null);
    const items = rows.map((r) => ({
      title: r.title,
      year: r.year,
      media_type: r.media_type,
      rating: normalizeRating(r.ratingRaw),
    }));
    const acc = { imported: 0, duplicate: 0, not_found: 0, error: 0, notFound: [] };
    setProgress({ done: 0, total: items.length });

    for (let i = 0; i < items.length; i += BATCH) {
      const chunk = items.slice(i, i + BATCH);
      try {
        const res = await api.importCsv(chunk);
        (res.results || []).forEach((r) => {
          if (r.status === 'imported') acc.imported++;
          else if (r.status === 'duplicate') acc.duplicate++;
          else if (r.status === 'not_found') { acc.not_found++; acc.notFound.push(r.title); }
          else acc.error++;
        });
      } catch {
        acc.error += chunk.length;
      }
      setProgress({ done: Math.min(i + BATCH, items.length), total: items.length });
      setReport({ ...acc });
    }

    setImporting(false);
    reloadLists();
    addToast(`Import completato: ${acc.imported} aggiunti`);
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      await api.exportCsv();
    } catch {
      addToast('Errore durante l\'esportazione');
    } finally {
      setExporting(false);
    }
  };

  const pct = progress.total ? Math.round((progress.done / progress.total) * 100) : 0;

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Importa da CSV</h1>
        <p className="page-subtitle">
          Da Letterboxd, IMDb o un CSV con colonne
          <code> title, year, type, rating</code>
        </p>
      </div>

      {/* Dropzone */}
      <div
        className={`dropzone ${dragOver ? 'over' : ''}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          hidden
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        />
        <Upload size={28} />
        <p><strong>Trascina qui il CSV</strong> o clicca per sceglierlo</p>
        {fileName && <p className="dropzone-file"><FileText size={14} /> {fileName}</p>}
      </div>

      {parseError && <div className="auth-error" style={{ marginTop: 16 }}>{parseError}</div>}

      {/* Riepilogo + opzioni */}
      {rows.length > 0 && !report && (
        <div className="import-summary">
          <div className="import-summary-row">
            <span><strong>{rows.length}</strong> titoli trovati nel file</span>
          </div>
          <div className="import-summary-row">
            <label htmlFor="scale">Scala dei voti</label>
            <select id="scale" className="filter-select" value={scale} onChange={(e) => setScale(e.target.value)}>
              <option value="auto">Auto (rilevata: su {detectedScale})</option>
              <option value="5">Su 5 (Letterboxd) → convertita a 10</option>
              <option value="10">Su 10</option>
            </select>
          </div>
          <button className="btn btn-primary" onClick={startImport} disabled={importing}>
            <Upload size={16} /> {importing ? 'Importazione…' : `Importa ${rows.length} titoli`}
          </button>
          <p className="import-note">
            La ricerca su TMDB è per titolo (+ anno se presente) e prende il primo risultato.
            I duplicati già in lista vengono saltati.
          </p>
        </div>
      )}

      {/* Progresso */}
      {importing && (
        <div className="import-progress">
          <div className="import-progress-bar">
            <div className="import-progress-fill" style={{ width: `${pct}%` }} />
          </div>
          <span>{progress.done}/{progress.total} ({pct}%)</span>
        </div>
      )}

      {/* Report finale */}
      {report && !importing && (
        <div className="import-report">
          <div className="import-report-head">
            <CheckCircle2 size={20} /> Import completato
          </div>
          <div className="import-report-stats">
            <div><strong>{report.imported}</strong> aggiunti</div>
            <div><strong>{report.duplicate}</strong> già presenti</div>
            <div><strong>{report.not_found}</strong> non trovati</div>
            {report.error > 0 && <div><strong>{report.error}</strong> errori</div>}
          </div>

          {report.notFound.length > 0 && (
            <details className="import-notfound">
              <summary>Titoli non trovati ({report.notFound.length})</summary>
              <ul>{report.notFound.map((t, i) => <li key={i}>{t}</li>)}</ul>
            </details>
          )}

          <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
            <button className="btn btn-primary" onClick={() => navigate('/watched')}>
              Vai ai visti
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => { setRows([]); setFileName(''); setReport(null); }}
            >
              <X size={15} /> Importa un altro file
            </button>
          </div>
        </div>
      )}

      {/* Esportazione */}
      <div className="import-summary" style={{ marginTop: 28 }}>
        <div className="import-summary-row">
          <strong>Esporta la tua libreria</strong>
        </div>
        <p className="import-note">
          Scarica un CSV con tutti i tuoi titoli (visti e da vedere), voti inclusi.
          Puoi reimportarlo qui o tenerlo come backup.
        </p>
        <button className="btn btn-secondary" onClick={handleExport} disabled={exporting}>
          <Download size={16} /> {exporting ? 'Preparazione…' : 'Scarica CSV'}
        </button>
      </div>
    </>
  );
}
