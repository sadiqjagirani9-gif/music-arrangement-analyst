// @vitest-environment jsdom
import '@testing-library/jest-dom/vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { QQMusicSearch } from './QQMusicSearch';

afterEach(() => vi.restoreAllMocks());

test('searches QQ Music and requests local upload when audio is unavailable', async () => {
  const track = { source: 'qq_music', source_id: 'mid-1', title: '晴天', artists: ['周杰伦'], album: '叶惠美', duration_seconds: 269, access: { status: 'requires_upload', reason: '需要上传' } };
  vi.spyOn(globalThis, 'fetch')
    .mockResolvedValueOnce(new Response(JSON.stringify({ page: 1, page_size: 10, total: 1, cached: false, items: [track] }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ detail: { code: 'local_upload_required', message: '请上传本地音频', track } }), { status: 409 }));
  const needUpload = vi.fn();
  render(<QQMusicSearch api="" busy={false} onAnalysis={vi.fn()} onNeedUpload={needUpload} onError={vi.fn()}/>);
  fireEvent.change(screen.getByPlaceholderText('输入歌曲、歌手或专辑'), { target: { value: '晴天' } });
  fireEvent.click(screen.getByRole('button', { name: '搜索' }));
  expect(await screen.findByText('周杰伦 · 叶惠美')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '添加到分析' }));
  await waitFor(() => expect(needUpload).toHaveBeenCalledWith(expect.objectContaining({ source_id: 'mid-1' }), '请上传本地音频'));
});
