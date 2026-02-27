import { NextResponse } from 'next/server';

export function middleware(request) {
  // Skip auth for the login page and auth API
  if (
    request.nextUrl.pathname === '/login' ||
    request.nextUrl.pathname === '/api/auth'
  ) {
    return NextResponse.next();
  }

  const authCookie = request.cookies.get('estate-auth')?.value;
  if (authCookie === 'authenticated') {
    return NextResponse.next();
  }

  return NextResponse.redirect(new URL('/login', request.url));
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
