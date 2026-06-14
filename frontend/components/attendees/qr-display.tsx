"use client";

import { useRef, useState, useEffect } from "react";
import QRCode from "react-qr-code";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LogoMark } from "@/components/brand/logo";

interface QRDisplayProps {
  slug: string;
}

const MARK_SRC = "/squadsync-mark.png";

// Rounded-rect path (manual — avoids relying on CanvasRenderingContext2D.roundRect typings).
function roundRectPath(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

export function QRDisplay({ slug }: QRDisplayProps) {
  const [url, setUrl] = useState("");
  const qrRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // window.location is only available post-mount (SSR-safe).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setUrl(`${window.location.origin}/join/${slug}`);
  }, [slug]);

  const downloadQR = () => {
    const svg = qrRef.current?.querySelector("svg");
    if (!svg) return;
    const svgData = new XMLSerializer().serializeToString(svg);
    // Use encodeURIComponent to handle Unicode safely (avoids btoa limitation)
    const svgDataUri = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svgData)}`;
    // Render at 512px for a crisp, printable export (the SVG scales cleanly).
    const size = 512;
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const qrImg = new Image();
    qrImg.onload = () => {
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, size, size);
      ctx.drawImage(qrImg, 0, 0, size, size);
      // Composite the hexagon mark over the center on a rounded white backing.
      // level="H" (30% error correction) keeps the code scannable under the mark.
      const mark = new Image();
      mark.onload = () => {
        const box = size * 0.26;
        const pad = box * 0.14;
        const inner = box - pad * 2;
        const x = (size - box) / 2;
        const y = (size - box) / 2;
        ctx.fillStyle = "#ffffff";
        roundRectPath(ctx, x, y, box, box, box * 0.2);
        ctx.fill();
        ctx.drawImage(mark, x + pad, y + pad, inner, inner);
        const a = document.createElement("a");
        a.download = `squadsync-qr-${slug}.png`;
        a.href = canvas.toDataURL("image/png");
        a.click();
      };
      mark.src = MARK_SRC;
    };
    qrImg.src = svgDataUri;
  };

  if (!url) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Registration QR Code</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col items-center gap-4">
        <div ref={qrRef} className="relative p-4 bg-white rounded-lg border">
          <QRCode value={url} size={160} level="H" />
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <span className="rounded-md bg-white p-1 shadow-sm ring-1 ring-black/5">
              <LogoMark className="h-9 w-9" />
            </span>
          </div>
        </div>
        <p className="text-xs text-muted-foreground text-center break-all">{url}</p>
        <Button variant="outline" size="sm" onClick={downloadQR}>
          <Download className="mr-2 h-3.5 w-3.5" /> Download PNG
        </Button>
      </CardContent>
    </Card>
  );
}
