import { NextRequest, NextResponse } from 'next/server';
import { getProvider } from '@/lib/providers';

type LyricData = {
  songid: string;
  provider: string;
  lines: Array<{ time: number; text: string }>;
  lrc: string;
};

type LyricCapableProvider = {
  getLyric?: (id: string, extra?: unknown) => Promise<LyricData>;
};

function parseExtra(value: string | null) {
  if (!value) return undefined;
  try {
    return JSON.parse(value) as unknown;
  } catch {
    return undefined;
  }
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const id = searchParams.get('id');
  const providerName = searchParams.get('provider') || 'netease';
  const extra = parseExtra(searchParams.get('extra'));

  if (!id) {
    return NextResponse.json({ error: 'Missing id' }, { status: 400 });
  }

  try {
    const provider = getProvider(providerName) as LyricCapableProvider;
    if (!provider.getLyric) {
      return NextResponse.json({
        songid: id,
        provider: providerName,
        lines: [],
        lrc: '',
      });
    }

    const lyric = await provider.getLyric(id, extra);
    return NextResponse.json(lyric);
  } catch (error) {
    console.error('Lyric error:', error);
    return NextResponse.json({ error: 'Failed to get lyric' }, { status: 500 });
  }
}
