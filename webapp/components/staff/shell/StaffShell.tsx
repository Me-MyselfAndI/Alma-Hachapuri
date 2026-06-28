"use client";

import { StaffHeader } from "@/components/staff/shell/StaffHeader";

type StaffShellProps = {
  children: React.ReactNode;
};

export function StaffShell({ children }: StaffShellProps) {
  return (
    <div className="flex min-h-full flex-col bg-background">
      <StaffHeader />
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8">{children}</main>
    </div>
  );
}
