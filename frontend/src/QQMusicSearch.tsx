import { useState, type FormEvent } from 'react';
import { ChevronLeft, ChevronRight, ExternalLink, FileAudio, Loader2, Music2, Search } from 'lucide-react';

export type SourceTrack = {
  source: string; source_id: string; title: string; artists: string[]; album: string;
  duration_seconds: number; cover_url?: string; public_url?: string;
  access: { status: string; reason: string };
};
type SearchPage = { page: number; page_size: number; total: number; cached: boolean; items: SourceTrack[] };

const formatDuration = (seconds: number) => `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;

export function QQMusicSearch({ api, busy, onAnalysis, onNeedUpload, onError }: {
  api: string; busy: boolean; onAnalysis: (value: any) => void;
  onNeedUpload: (track: SourceTrack, message: string) => void; onError: (message: string) => void;
}) {
  const [query, setQuery] = useState('');
  const [scope, setScope] = useState('all');
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<SearchPage | null>(null);

  const search = async (event?: FormEvent, page = 1) => {
    event?.preventDefault();
    if (!query.trim()) return;
    setSearching(true); onError('');
    try {
      const params = new URLSearchParams({ q: query.trim(), scope, page: String(page), page_size: '10' });
      const response = await fetch(`${api}/api/sources/qq/search?${params}`);
      if (!response.ok) throw new Error(await response.text());
      setResults(await response.json());
    } catch (error) { onError(error instanceof Error ? error.message : 'QQ 音乐搜索失败'); }
    finally { setSearching(false); }
  };

  const addToAnalysis = async (track: SourceTrack) => {
    onError('');
    try {
      const response = await fetch(`${api}/api/sources/qq/import`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ song_id: track.source_id }) });
      const payload = await response.json();
      if (response.status === 409) {
        onNeedUpload(payload.detail?.track || track, payload.detail?.message || '当前没有可合法分析的公开音频，请上传本地文件。');
        return;
      }
      if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : '导入失败');
      onAnalysis(payload);
    } catch (error) { onError(error instanceof Error ? error.message : '导入失败'); }
  };

  return <section className="source-browser">
    <div className="source-heading"><div><div className="eyebrow">QQ MUSIC SOURCE</div><h2>搜索 QQ 音乐</h2><p className="muted">歌曲信息来自非官方网页接口，不保证长期稳定；搜索无需登录。</p></div><Music2 size={32}/></div>
    <form className="search-form" onSubmit={event => search(event)}><Search size={18}/><input value={query} onChange={event => setQuery(event.target.value)} placeholder="输入歌曲、歌手或专辑"/><select value={scope} onChange={event => setScope(event.target.value)}><option value="all">全部</option><option value="song">歌曲</option><option value="artist">歌手</option><option value="album">专辑</option></select><button disabled={searching}>{searching ? <Loader2 className="spin" size={17}/> : '搜索'}</button></form>
    {!results && <div className="empty compact"><FileAudio size={36}/><h3>选择一个音乐来源</h3><p>搜索 QQ 音乐并导入公开可访问音频，或直接上传你合法取得的本地音频。</p></div>}
    {results && <><div className="result-meta"><span>{results.total} 个相关结果 · 第 {results.page} 页</span><span>{results.cached ? '缓存结果' : '实时查询'}</span></div><div className="song-list">{results.items.map(track => <article className="song" key={track.source_id}><img src={track.cover_url} alt=""/><div className="song-main"><h3>{track.title}</h3><p>{track.artists.join(' / ') || '未知歌手'} · {track.album}</p><small>ID {track.source_id} · {formatDuration(track.duration_seconds)}</small></div><div className="song-actions">{track.public_url && <a href={track.public_url} target="_blank" rel="noreferrer" title="在 QQ 音乐查看"><ExternalLink size={16}/></a>}<button disabled={busy} onClick={() => addToAnalysis(track)}>添加到分析</button></div></article>)}</div><div className="pagination"><button disabled={results.page <= 1 || searching} onClick={() => search(undefined, results.page - 1)}><ChevronLeft size={16}/> 上一页</button><button disabled={results.items.length < results.page_size || searching} onClick={() => search(undefined, results.page + 1)}>下一页 <ChevronRight size={16}/></button></div></>}
  </section>;
}
