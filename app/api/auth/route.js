import { NextResponse } from 'next/server';

const PASSWORD = process.env.SITE_PASSWORD || 'meowmix';

export async function POST(request) {
  const { password } = await request.json();

  if (password === PASSWORD) {
    const response = NextResponse.json({ ok: true });
    response.cookies.set('estate-auth', 'authenticated', {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 60 * 60 * 24 * 90, // 90 days
    });
    return response;
  }

  return NextResponse.json({ ok: false }, { status: 401 });
}
