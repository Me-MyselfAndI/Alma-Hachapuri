"use client";

import { StaffHeader } from "@/components/staff/shell/StaffHeader";

type StaffShellProps = {
  children: React.ReactNode;
};

export function StaffShell({ children }: StaffShellProps) {
  return (
    <div className="flex min-h-full flex-col">
      <StaffHeader />
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6">
        {children}
      </main>
    </div>
  );
}
