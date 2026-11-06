import { useMemo, useState, type ReactNode } from 'react';
import { Activity, Download, FileAudio, FileMusic, Gauge, Play, Upload, Volume2 } from 'lucide-react';

type Analysis = { id: string; audio: any; key: any; rhythm: any; structure: any[]; instruments: any[]; timeline: any; chords: any[]; report_markdown: string };
const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function App() {
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [activeTrack, setActiveTrack] = useState('Vocals');
  const upload = async (file: File) => {
    setBusy(true); setError('');
    const body = new FormData(); body.append('file', file);
    try { const response = await fetch(`${API}/api/analyze`, { method: 'POST', body }); if (!response.ok) throw new Error(await response.text()); setAnalysis(await response.json()); }
    catch (e) { setError(e instanceof Error ? e.message : '分析失败'); } finally { setBusy(false); }
  };
  const tracks = useMemo(() => analysis?.timeline?.tracks || [], [analysis]);
  return <main className="shell">
    <header className="topbar"><div className="brand"><Activity size={18}/> <span>Music Arrangement Analyst</span></div><div className="status"><span className="dot"/> LOCAL ENGINE</div></header>
    <section className="workspace">
      <aside className="sidebar"><div className="eyebrow">ANALYSIS CONSOLE</div><h1>把歌曲拆成可编辑的编曲决策</h1><p className="muted">测量特征、保守推断和可编辑 MIDI 草案集中在一个时间轴里。</p>
        <label className="upload"><Upload size={17}/><span>{busy ? '正在分析…' : '上传音频'}</span><input type="file" accept="audio/*" disabled={busy} onChange={e => e.target.files?.[0] && upload(e.target.files[0])}/></label>
        <div className="pipeline">{['音频读取','节奏分析','和声分析','结构识别','轨道候选','报告生成'].map((x,i)=><div className={busy && i===0 ? 'step active' : 'step'} key={x}><span>{String(i+1).padStart(2,'0')}</span>{x}</div>)}</div>
        {error && <div className="error">{error}</div>}
      </aside>
      <section className="content">{!analysis ? <div className="empty"><FileAudio size={42}/><h2>还没有分析任务</h2><p>上传 MP3、WAV、FLAC 或 M4A，后端会返回测量结果、置信度和时间轴数据。</p></div> : <>
        <div className="summary"><div><div className="eyebrow">CURRENT ANALYSIS</div><h2>{analysis.key.key} {analysis.key.mode}</h2><span className="muted">{analysis.audio.duration}s · {analysis.audio.bpm || '—'} BPM · {analysis.rhythm.meter}</span></div><div className="metrics"><Metric icon={<Gauge size={16}/>} label="BPM" value={analysis.audio.bpm || '—'}/><Metric icon={<Volume2 size={16}/>} label="RMS" value={analysis.audio.rms}/><Metric icon={<FileMusic size={16}/>} label="CHORDS" value={analysis.chords.length}/></div></div>
        <div className="section-title"><span>ARRANGEMENT TIMELINE</span><button onClick={() => window.open(`${API}/api/analysis/${analysis.id}/report.md`)}><Download size={15}/> Report</button></div>
        <div className="timeline"><div className="ruler"><span>0:00</span><span>{Math.round(analysis.audio.duration/2)}s</span><span>{Math.round(analysis.audio.duration)}s</span></div>{analysis.timeline.sections.map((s: any)=><div className="section-block" style={{left:`${s.start/analysis.audio.duration*100}%`,width:`${(s.end-s.start)/analysis.audio.duration*100}%`}} key={`${s.name}-${s.start}`}>{s.name}</div>)}{tracks.map((track: any)=><button className={`track ${activeTrack===track.name?'selected':''}`} onClick={() => setActiveTrack(track.name)} key={track.name}><span className="track-name">{track.name}</span><span className="track-lane">{track.segments.map((seg:any)=><span className="activity" style={{left:`${seg.start/analysis.audio.duration*100}%`,width:`${Math.max(2,(seg.end-seg.start)/analysis.audio.duration*100)}%`}} key={seg.start}/>)}</span></button>)}</div>
        <div className="detail"><div><div className="eyebrow">TRACK DETAIL</div><h3>{activeTrack}</h3><p className="muted">{analysis.instruments.find(x => x.name===activeTrack)?.function || '未检测到可靠候选，保持空轨以避免过度断言。'}</p></div><div className="confidence">置信度 <strong>{analysis.instruments.find(x => x.name===activeTrack)?.confidence || 0}</strong></div></div>
        <div className="cards"><article><div className="eyebrow">STRUCTURE</div>{analysis.structure.map(s=><div className="row" key={s.start}><b>{s.name}</b><span>{s.start}s–{s.end}s</span><small>{s.energy}</small></div>)}</article><article><div className="eyebrow">CHORD HYPOTHESES</div>{analysis.chords.slice(0,6).map(c=><div className="row" key={c.start}><b>{c.name}</b><span>{c.start}s–{c.end}s</span><small>{c.confidence}</small></div>)}</article></div>
      </>}</section>
    </section>
  </main>
}
function Metric({icon,label,value}:{icon:ReactNode;label:string;value:ReactNode}) { return <div className="metric">{icon}<span>{label}</span><strong>{value}</strong></div> }
