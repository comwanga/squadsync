"use client";

import { useRef, useState, useEffect } from "react";
import QRCode from "react-qr-code";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface QRDisplayProps {
  slug: string;
}

export function QRDisplay({ slug }: QRDisplayProps) {
  const [url, setUrl] = useState("");
  const qrRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setUrl(`${window.location.origin}/join/${slug}`);
  }, [slug]);

  const downloadQR = () => {
    const svg = qrRef.current?.querySelector("svg");
    if (!svg) return;
    const svgData = new XMLSerializer().serializeToString(svg);
    // Use encodeURIComponent to handle Unicode safely (avoids btoa limitation)
    const svgDataUri = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svgData)}`;
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    const img = new Image();
    img.onload = () => {
      // Use explicit size (160px matches QRCode size prop) since SVG may report 0 naturalWidth
      const size = 160;
      canvas.width = size;
      canvas.height = size;
      ctx?.drawImage(img, 0, 0, size, size);
      const a = document.createElement("a");
      a.download = `squadsync-qr-${slug}.png`;
      a.href = canvas.toDataURL("image/png");
      a.click();
    };
    img.src = svgDataUri;
  };

  if (!url) return null;

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
