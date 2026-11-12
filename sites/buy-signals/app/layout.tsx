import type { Metadata } from 'next';
import './globals.css';
export const metadata:Metadata={title:'PreDash Classroom · 매수 신호 점수표',description:'공식 일별 시세와 확인 가능한 근거로 살펴보는 개인 매수 신호 점수표.',robots:{index:false,follow:false},icons:{icon:'/favicon.svg'}};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="ko"><body>{children}</body></html>;}
