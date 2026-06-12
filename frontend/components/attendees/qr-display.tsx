"use client";

import { useRef } from "react";
import QRCode from "react-qr-code";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface QRDisplayProps {
  slug: string;
}

export function QRDisplay({ slug }: QRDisplayProps) {
  const baseUrl = typeof window !== "undefined" ? window.location.origin : "";
  const url = `${baseUrl}/join/${slug}`;
  const qrRef = useRef<HTMLDivElement>(null);

  const downloadQR = () => {
    const svg = qrRef.current?.querySelector("svg");
    if (!svg) return;
    const svgData = new XMLSerializer().serializeToString(svg);
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    const img = new Image();
    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx?.drawImage(img, 0, 0);
      const a = document.createElement("a");
      a.download = `squadsync-qr-${slug}.png`;
      a.href = canvas.toDataURL("image/png");
      a.click();
    };
    img.src = `data:image/svg+xml;base64,${btoa(svgData)}`;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Registration QR Code</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col items-center gap-4">
        <div ref={qrRef} className="p-4 bg-white rounded-lg border">
          <QRCode value={url} size={160} />
        </div>
        <p className="text-xs text-muted-foreground text-center break-all">{url}</p>
        <Button variant="outline" size="sm" onClick={downloadQR}>
          <Download className="mr-2 h-3.5 w-3.5" /> Download PNG
        </Button>
      </CardContent>
    </Card>
  );
}
