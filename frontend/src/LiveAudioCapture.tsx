import { useEffect, useRef, useState } from 'react';
import { Circle, Download, MonitorSpeaker, Pause, Play, RefreshCw, Square, Waves } from 'lucide-react';
import './LiveAudioCapture.css';

type Device = { id: string; name: string; backend: string; kind: string; is_loopback: boolean; is_default: boolean; max_channels: number };
type Session = {
  id: string; state: string; error?: string; device: Device; sample_rate: number; channels: number;
  duration_seconds: number; file_size_bytes: number; rms: number; peak: number; level_dbfs: number;
  waveform: number[]; analysis_progress: number; analysis_id?: string; validation?: any; download_available: boolean;
};

const terminalStates = new Set(['completed', 'invalid', 'error']);
const stateLabels: Record<string, string> = { starting: '正在连接', recording: '录制中', paused: '已暂停', stopping: '正在停止', processing: '检查音频', analyzing: '分析中', completed: '已完成', invalid: '无效音频', error: '错误' };
const formatTime = (seconds: number) => `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;
const formatBytes = (bytes: number) => bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / 1024 / 1024).toFixed(2)} MB`;

export function LiveAudioCapture({ api, onAnalysis, onError }: { api: string; onAnalysis: (analysis: any) => void; onError: (message: string) => void }) {
  const [devices, setDevices] = useState<Device[]>([]);
  const [deviceId, setDeviceId] = useState('');
  const [sampleRate, setSampleRate] = useState(48000);
  const [maxDuration, setMaxDuration] = useState('');
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const loadDevices = async () => {
    setLoading(true); onError('');
    try {
      const response = await fetch(`${api}/api/capture/devices`);
      if (!response.ok) throw new Error(await response.text());
      const payload = await response.json();
      setDevices(payload.devices);
      const preferred = payload.devices.find((device: Device) => device.is_default && device.is_loopback) || payload.devices.find((device: Device) => device.is_loopback) || payload.devices[0];
      if (preferred) setDeviceId(preferred.id);
    } catch (error) { onError(error instanceof Error ? error.message : '无法读取音频设备'); }
    finally { setLoading(false); }
  };

  useEffect(() => { void loadDevices(); }, []);
  useEffect(() => {
    if (!session || terminalStates.has(session.state)) return;
    const timer = window.setInterval(async () => {
      try {
        const response = await fetch(`${api}/api/capture/sessions/${session.id}`);
        if (response.ok) setSession(await response.json());
      } catch { /* The next poll can recover a transient local connection failure. */ }
    }, 200);
    return () => window.clearInterval(timer);
  }, [api, session?.id, session?.state]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ratio = window.devicePixelRatio || 1;
    const width = Math.max(320, canvas.clientWidth);
    const height = 180;
    canvas.width = width * ratio; canvas.height = height * ratio;
    const context = canvas.getContext('2d'); if (!context) return;
    context.scale(ratio, ratio); context.clearRect(0, 0, width, height);
    context.strokeStyle = '#253037'; context.lineWidth = 1;
    context.beginPath(); context.moveTo(0, height / 2); context.lineTo(width, height / 2); context.stroke();
    const values = session?.waveform || [];
    if (!values.length) return;
    context.strokeStyle = '#76d6ad'; context.lineWidth = 1.5; context.beginPath();
    values.forEach((value, index) => { const x = index / Math.max(1, values.length - 1) * width; const y = height / 2 - value * height * .43; index ? context.lineTo(x, y) : context.moveTo(x, y); });
    context.stroke();
  }, [session?.waveform]);

  const request = async (path: string, body?: unknown) => {
    const response = await fetch(`${api}${path}`, { method: 'POST', headers: body ? { 'Content-Type': 'application/json' } : undefined, body: body ? JSON.stringify(body) : undefined });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || '操作失败');
    setSession(payload);
  };
  const start = async () => {
    onError('');
    try { await request('/api/capture/sessions', { device_id: deviceId, sample_rate: sampleRate, channels: 2, max_duration_seconds: maxDuration ? Number(maxDuration) : null, auto_analyze: true }); }
    catch (error) { onError(error instanceof Error ? error.message : '无法开始录制'); }
  };
  const action = async (name: 'pause' | 'resume' | 'stop') => {
    if (!session) return;
    try { await request(`/api/capture/sessions/${session.id}/${name}`); }
    catch (error) { onError(error instanceof Error ? error.message : '录制控制失败'); }
  };
  const openAnalysis = async () => {
    if (!session?.analysis_id) return;
    const response = await fetch(`${api}/api/analysis/${session.analysis_id}`);
    if (response.ok) onAnalysis(await response.json());
  };
  const levelPercent = Math.max(0, Math.min(100, ((session?.level_dbfs || -60) + 60) / 60 * 100));
  const active = session && !terminalStates.has(session.state);

  return <section className="capture-page">
    <div className="capture-heading"><div><div className="eyebrow">LIVE AUDIO CAPTURE</div><h2>实时音频捕获</h2><p className="muted">使用 Windows WASAPI Loopback 捕获系统正常输出，不绕过 DRM 或访问控制。</p></div><Waves size={34}/></div>
    <div className="capture-layout">
      <section className="capture-main">
        <div className="wave-panel"><canvas ref={canvasRef}/><div className="wave-status"><span className={`record-dot ${session?.state === 'recording' ? 'live' : ''}`}/>{stateLabels[session?.state || ''] || '等待录制'}<strong>{formatTime(session?.duration_seconds || 0)}</strong></div></div>
        <div className="level-panel"><span>INPUT LEVEL</span><div className="level-track"><i style={{ width: `${levelPercent}%` }}/></div><b>{session?.level_dbfs?.toFixed(1) || '-96.0'} dBFS</b></div>
        <div className="capture-controls">
          {!active && <button className="record-button" disabled={!deviceId || loading} onClick={start}><Circle size={17}/> 开始录制</button>}
          {session?.state === 'recording' && <button onClick={() => action('pause')}><Pause size={17}/> 暂停</button>}
          {session?.state === 'paused' && <button onClick={() => action('resume')}><Play size={17}/> 继续</button>}
          {active && ['starting','recording','paused'].includes(session.state) && <button onClick={() => action('stop')}><Square size={16}/> 停止</button>}
          {session?.download_available && <a href={`${api}/api/capture/sessions/${session.id}/audio.wav`}><Download size={16}/> WAV</a>}
          {session?.analysis_id && <button onClick={openAnalysis}>打开分析结果</button>}
        </div>
        {session && (session.state === 'processing' || session.state === 'analyzing' || terminalStates.has(session.state)) && <div className="analysis-progress"><div><span>分析进度</span><b>{session.analysis_progress}%</b></div><div className="progress-track"><i style={{width:`${session.analysis_progress}%`}}/></div>{session.validation && <p>{session.validation.valid ? `音频有效 · ${session.validation.sample_rate} Hz · 静音 ${(session.validation.silent_ratio*100).toFixed(1)}%` : session.validation.issues.join('；')}</p>}{session.error && <p className="capture-error">{session.error}</p>}</div>}
      </section>
      <aside className="capture-settings"><div className="setting-title"><MonitorSpeaker size={17}/><span>录制设置</span><button title="刷新设备" onClick={loadDevices}><RefreshCw size={15}/></button></div><label>音频设备<select disabled={!!active} value={deviceId} onChange={event => setDeviceId(event.target.value)}>{!devices.length && <option value="">未检测到设备</option>}{devices.map(device => <option value={device.id} key={device.id}>{device.is_loopback ? '[Loopback] ' : ''}{device.name}</option>)}</select></label><label>采样率<select disabled={!!active} value={sampleRate} onChange={event => setSampleRate(Number(event.target.value))}><option value={48000}>48000 Hz</option><option value={44100}>44100 Hz</option></select></label><label>最大时长（秒）<input disabled={!!active} type="number" min="1" max="14400" value={maxDuration} onChange={event => setMaxDuration(event.target.value)} placeholder="不限"/></label><div className="capture-facts"><div><span>文件大小</span><b>{formatBytes(session?.file_size_bytes || 0)}</b></div><div><span>声道</span><b>{session?.channels || 2}</b></div><div><span>峰值</span><b>{((session?.peak || 0)*100).toFixed(1)}%</b></div></div><p>如果受保护内容只产生静音，系统会停止分析并提示改用合法取得的本地音频。</p></aside>
    </div>
  </section>;
}
