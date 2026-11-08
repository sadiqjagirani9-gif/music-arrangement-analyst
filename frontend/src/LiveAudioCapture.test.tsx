// @vitest-environment jsdom
import '@testing-library/jest-dom/vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { LiveAudioCapture } from './LiveAudioCapture';

afterEach(() => vi.restoreAllMocks());

test('loads loopback devices and starts a capture session', async () => {
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null);
  const device = { id: 'soundcard:test', name: 'Speakers', backend: 'soundcard_wasapi', kind: 'output_loopback', is_loopback: true, is_default: true, max_channels: 2 };
  const session = { id: 'capture-1', state: 'completed', device, sample_rate: 48000, channels: 2, duration_seconds: 2, file_size_bytes: 1000, rms: .1, peak: .2, level_dbfs: -20, waveform: [], analysis_progress: 100, download_available: true };
  const fetchMock = vi.spyOn(globalThis, 'fetch')
    .mockResolvedValueOnce(new Response(JSON.stringify({ devices: [device], supported_sample_rates: [44100, 48000] }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify(session), { status: 200 }));
  render(<LiveAudioCapture api="" onAnalysis={vi.fn()} onError={vi.fn()}/>);
  expect(await screen.findByRole('option', { name: '[Loopback] Speakers' })).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '开始录制' }));
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/capture/sessions', expect.objectContaining({ method: 'POST' })));
  expect(await screen.findByText('已完成')).toBeInTheDocument();
});
