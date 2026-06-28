"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState, startTransition } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { staffFetch } from "@/lib/staff-api";
import type { LeadListItem, LeadState, Paginated } from "@/lib/types";

import { LeadFilters } from "./LeadFilters";
import { LeadPagination } from "./LeadPagination";
import { LeadTable } from "./LeadTable";

const VALID_STATES = new Set<LeadState>([
  "PENDING",
  "REACHED_OUT",
  "QUALIFIED",
  "DISQUALIFIED",
  "CLOSED",
]);

function parseState(value: string | null): LeadState | "" {
  if (!value) {
    return "";
  }
  return VALID_STATES.has(value as LeadState) ? (value as LeadState) : "";
}

function parsePage(value: string | null): number {
  const page = Number.parseInt(value ?? "1", 10);
  return Number.isFinite(page) && page >= 1 ? page : 1;
}

function buildLeadsQuery(state: LeadState | "", mine: boolean, page: number): string {
  const params = new URLSearchParams();
  if (state) {
    params.set("state", state);
  }
  if (mine) {
    params.set("mine", "true");
  }
  if (page > 1) {
    params.set("page", String(page));
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

function buildLeadsPath(state: LeadState | "", mine: boolean, page: number): string {
  return `/leads${buildLeadsQuery(state, mine, page)}`;
}

function readLeadsError(status: number, body: unknown): string {
  if (status === 403) {
    return "You don't have permission to view leads. Your role needs the read leads capability.";
  }
  if (typeof body === "object" && body !== null && "detail" in body) {
    const detail = (body as { detail?: string }).detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
  }
  return "Something went wrong loading leads. Please try again.";
}

export function LeadListPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const state = parseState(searchParams.get("state"));
  const mine = searchParams.get("mine") === "true";
  const page = parsePage(searchParams.get("page"));

  const [items, setItems] = useState<LeadListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);

  const updateUrl = useCallback(
    (nextState: LeadState | "", nextMine: boolean, nextPage: number) => {
      router.replace(buildLeadsPath(nextState, nextMine, nextPage));
    },
    [router],
  );

  const loadLeads = useCallback(async () => {
    setLoading(true);
    setError(null);
    setForbidden(false);

    const params = new URLSearchParams();
    if (state) {
      params.set("state", state);
    }
    if (mine) {
      params.set("mine", "true");
    }
    params.set("page", String(page));
    params.set("page_size", "20");

    const result = await staffFetch<Paginated<LeadListItem>>(
      `/api/v1/leads?${params.toString()}`,
    );

    if (result.ok) {
      setItems(result.data.items);
      setTotal(result.data.total);
      setPageSize(result.data.page_size);
      setLoading(false);
      return;
    }

    if (result.status === 401) {
      router.replace(`/login?next=${encodeURIComponent(buildLeadsPath(state, mine, page))}`);
      return;
    }

    if (result.status === 403) {
      setForbidden(true);
      setItems([]);
      setTotal(0);
      setLoading(false);
      return;
    }

    setError(readLeadsError(result.status, result.body));
    setItems([]);
    setTotal(0);
    setLoading(false);
  }, [mine, page, router, state]);

  useEffect(() => {
    startTransition(() => {
      void loadLeads();
    });
  }, [loadLeads]);

  const hasActiveFilters = Boolean(state) || mine;

  function handleStateChange(nextState: LeadState | "") {
    updateUrl(nextState, mine, 1);
  }

  function handleMineChange(nextMine: boolean) {
    updateUrl(state, nextMine, 1);
  }

  function handlePageChange(nextPage: number) {
    updateUrl(state, mine, nextPage);
  }

  function handleClearFilters() {
    updateUrl("", false, 1);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Leads</h1>

      <LeadFilters
        state={state}
        mine={mine}
        onStateChange={handleStateChange}
        onMineChange={handleMineChange}
      />

      {forbidden ? (
        <Alert variant="destructive">
          <AlertTitle>Access denied</AlertTitle>
          <AlertDescription>
            You don&apos;t have permission to view leads. Your role needs the{" "}
            <strong>read leads</strong> capability.
          </AlertDescription>
        </Alert>
      ) : null}

      {error ? (
        <Alert variant="destructive">
          <AlertDescription className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <span>{error}</span>
            <Button variant="outline" size="sm" onClick={() => void loadLeads()}>
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      ) : null}

      {!forbidden && !error ? (
        <>
          <LeadTable items={items} loading={loading} />

          {!loading && items.length === 0 ? (
            <Alert>
              <AlertTitle>No leads found</AlertTitle>
              <AlertDescription>
                No leads match your filters.
                {hasActiveFilters ? (
                  <>
                    {" "}
                    <Link
                      href="/leads"
                      className="font-medium underline underline-offset-4"
                      onClick={(event) => {
                        event.preventDefault();
                        handleClearFilters();
                      }}
                    >
                      Clear filters
                    </Link>
                  </>
                ) : null}
              </AlertDescription>
            </Alert>
          ) : null}

          {!loading && items.length > 0 ? (
            <LeadPagination
              page={page}
              pageSize={pageSize}
              total={total}
              onPageChange={handlePageChange}
            />
          ) : null}
        </>
      ) : null}
    </div>
  );
}
