import React from 'react';

export function Spinner({ size = 24 }: { size?: number }) {
  const px = `${size}px`;
  return (
    <div
      className="inline-block animate-spin rounded-full border-2 border-primary border-t-transparent"
      style={{ width: px, height: px }}
      aria-label="Loading"
    />
  );
}
