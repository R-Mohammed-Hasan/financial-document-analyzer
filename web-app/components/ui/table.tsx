import * as React from 'react';

export function Table({ className = '', ...props }: React.HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="w-full overflow-x-auto">
      <table className={`w-full caption-bottom text-sm ${className}`} {...props} />
    </div>
  );
}

export function TableHeader({ className = '', ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return <thead className={`[&_tr]:border-b ${className}`} {...props} />;
}

export function TableBody({ className = '', ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={`[&_tr:last-child]:border-0 ${className}`} {...props} />;
}

export function TableRow({ className = '', ...props }: React.HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={`border-b transition-colors hover:bg-muted ${className}`} {...props} />;
}

export function TableHead({ className = '', ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={`h-10 px-3 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0 ${className}`}
      {...props}
    />
  );
}

export function TableCell({ className = '', ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td
      className={`p-3 align-middle [&:has([role=checkbox])]:pr-0 ${className}`}
      {...props}
    />
  );
}

export function TableCaption({ className = '', ...props }: React.HTMLAttributes<HTMLElement>) {
  return <caption className={`mt-4 text-sm text-muted-foreground ${className}`} {...props} />;
}
