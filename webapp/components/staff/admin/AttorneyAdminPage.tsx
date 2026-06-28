"use client";

import { Loader2, Plus, X } from "lucide-react";
import { useCallback, useEffect, useState, startTransition } from "react";

import { useSession } from "@/components/auth/SessionProvider";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { FadeIn } from "@/components/ui/fade-in";
import { Skeleton } from "@/components/ui/skeleton";
import { formatStaffApiError, staffFetch } from "@/lib/staff-api";
import { getPermissionMessage } from "@/lib/permission-messages";
import { cn } from "@/lib/utils";
import type { AccountRead, AccountUpdate, Paginated } from "@/lib/types";

type AttorneyFormMode = "create" | "edit";

type AttorneyFormValues = {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  work_email: string;
  is_default_assignee: boolean;
  is_active: boolean;
};

const EMPTY_CREATE: AttorneyFormValues = {
  email: "",
  password: "",
  first_name: "",
  last_name: "",
  work_email: "",
  is_default_assignee: false,
  is_active: true,
};

function accountToForm(account: AccountRead): AttorneyFormValues {
  return {
    email: account.email,
    password: "",
    first_name: account.first_name,
    last_name: account.last_name,
    work_email: account.work_email ?? "",
    is_default_assignee: account.is_default_assignee,
    is_active: account.is_active,
  };
}

function LoadingRows() {
  return (
    <>
      {Array.from({ length: 3 }).map((_, index) => (
        <TableRow key={index}>
          {Array.from({ length: 5 }).map((__, cellIndex) => (
            <TableCell key={cellIndex}>
              <Skeleton className="h-4 w-full" />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  );
}

export function AttorneyAdminPage() {
  const { user } = useSession();
  const canManage = user.permissions.includes("manage_users");

  const [items, setItems] = useState<AccountRead[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [formMode, setFormMode] = useState<AttorneyFormMode | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formValues, setFormValues] = useState<AttorneyFormValues>(EMPTY_CREATE);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const loadAttorneys = useCallback(async () => {
    if (!canManage) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    const result = await staffFetch<Paginated<AccountRead>>(
      `/api/v1/accounts?role=attorney&page=${page}&page_size=${pageSize}`,
    );

    setLoading(false);

    if (!result.ok) {
      setError(formatStaffApiError(result.status, result.body));
      return;
    }

    setItems(result.data.items);
    setTotal(result.data.total);
  }, [canManage, page, pageSize]);

  useEffect(() => {
    startTransition(() => {
      void loadAttorneys();
    });
  }, [loadAttorneys]);

  const openCreate = () => {
    setFormMode("create");
    setEditingId(null);
    setFormValues(EMPTY_CREATE);
    setFormError(null);
  };

  const openEdit = (account: AccountRead) => {
    setFormMode("edit");
    setEditingId(account.id);
    setFormValues(accountToForm(account));
    setFormError(null);
  };

  const closeForm = () => {
    setFormMode(null);
    setEditingId(null);
    setFormValues(EMPTY_CREATE);
    setFormError(null);
  };

  const handleSave = async () => {
    if (!formMode) {
      return;
    }

    setSaving(true);
    setFormError(null);

    if (formMode === "create") {
      const result = await staffFetch<AccountRead>("/api/v1/accounts", {
        method: "POST",
        json: {
          email: formValues.email.trim(),
          password: formValues.password,
          role: "attorney",
          first_name: formValues.first_name.trim(),
          last_name: formValues.last_name.trim(),
          work_email: formValues.work_email.trim() || null,
          is_default_assignee: formValues.is_default_assignee,
        },
      });

      setSaving(false);

      if (!result.ok) {
        setFormError(formatStaffApiError(result.status, result.body));
        return;
      }

      closeForm();
      void loadAttorneys();
      return;
    }

    if (!editingId) {
      setSaving(false);
      return;
    }

    const payload: AccountUpdate = {
      first_name: formValues.first_name.trim(),
      last_name: formValues.last_name.trim(),
      work_email: formValues.work_email.trim() || null,
      is_default_assignee: formValues.is_default_assignee,
      is_active: formValues.is_active,
    };

    if (formValues.password.trim()) {
      payload.password = formValues.password;
    }

    const result = await staffFetch<AccountRead>(
      `/api/v1/accounts/${editingId}`,
      { method: "PATCH", json: payload },
    );

    setSaving(false);

    if (!result.ok) {
      setFormError(formatStaffApiError(result.status, result.body));
      return;
    }

    closeForm();
    void loadAttorneys();
  };

  if (!canManage) {
    return (
      <Alert>
        <AlertTitle>Admin access required</AlertTitle>
        <AlertDescription>{getPermissionMessage("manage_users")}</AlertDescription>
      </Alert>
    );
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <FadeIn variant="fade" className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="font-heading text-3xl font-bold tracking-tight">
            Attorneys
          </h1>
          <p className="text-muted-foreground">
            Click a row to edit an attorney account.
          </p>
        </div>
        {!formMode ? (
          <Button type="button" onClick={openCreate}>
            <Plus className="size-4" aria-hidden />
            Add attorney
          </Button>
        ) : null}
      </div>

      {formMode ? (
        <Card>
          <CardHeader className="flex flex-row items-start justify-between gap-4">
            <div>
              <CardTitle>
                {formMode === "create" ? "Add attorney" : "Edit attorney"}
              </CardTitle>
              <CardDescription>
                {formMode === "create"
                  ? "Create a new attorney account. Role cannot be changed later."
                  : "Update profile, notification email, or reset password."}
              </CardDescription>
            </div>
            <Button type="button" variant="ghost" size="icon-sm" onClick={closeForm}>
              <X className="size-4" aria-hidden />
              <span className="sr-only">Close</span>
            </Button>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              {formMode === "create" ? (
                <>
                  <div className="space-y-2 sm:col-span-2">
                    <Label htmlFor="attorney-email">Login email</Label>
                    <Input
                      id="attorney-email"
                      type="email"
                      value={formValues.email}
                      onChange={(e) =>
                        setFormValues((v) => ({ ...v, email: e.target.value }))
                      }
                      disabled={saving}
                      autoComplete="off"
                    />
                  </div>
                  <div className="space-y-2 sm:col-span-2">
                    <Label htmlFor="attorney-password">Password</Label>
                    <Input
                      id="attorney-password"
                      type="password"
                      value={formValues.password}
                      onChange={(e) =>
                        setFormValues((v) => ({ ...v, password: e.target.value }))
                      }
                      disabled={saving}
                      minLength={8}
                      autoComplete="new-password"
                    />
                  </div>
                </>
              ) : (
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="attorney-email-readonly">Login email</Label>
                  <Input
                    id="attorney-email-readonly"
                    value={formValues.email}
                    disabled
                  />
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="attorney-first-name">First name</Label>
                <Input
                  id="attorney-first-name"
                  value={formValues.first_name}
                  onChange={(e) =>
                    setFormValues((v) => ({ ...v, first_name: e.target.value }))
                  }
                  disabled={saving}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="attorney-last-name">Last name</Label>
                <Input
                  id="attorney-last-name"
                  value={formValues.last_name}
                  onChange={(e) =>
                    setFormValues((v) => ({ ...v, last_name: e.target.value }))
                  }
                  disabled={saving}
                />
              </div>

              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="attorney-work-email">Work email (optional)</Label>
                <Input
                  id="attorney-work-email"
                  type="email"
                  value={formValues.work_email}
                  onChange={(e) =>
                    setFormValues((v) => ({ ...v, work_email: e.target.value }))
                  }
                  disabled={saving}
                  placeholder="Defaults to login email for notifications"
                />
              </div>

              {formMode === "edit" ? (
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="attorney-new-password">
                    New password (optional)
                  </Label>
                  <Input
                    id="attorney-new-password"
                    type="password"
                    value={formValues.password}
                    onChange={(e) =>
                      setFormValues((v) => ({ ...v, password: e.target.value }))
                    }
                    disabled={saving}
                    minLength={8}
                    autoComplete="new-password"
                    placeholder="Leave blank to keep current password"
                  />
                </div>
              ) : null}
            </div>

            <div className="flex flex-wrap gap-6">
              <div className="flex items-center gap-2">
                <Checkbox
                  id="attorney-default"
                  checked={formValues.is_default_assignee}
                  onCheckedChange={(checked) =>
                    setFormValues((v) => ({
                      ...v,
                      is_default_assignee: checked === true,
                    }))
                  }
                  disabled={saving}
                />
                <Label htmlFor="attorney-default" className="cursor-pointer font-normal">
                  Default assignee for new leads
                </Label>
              </div>

              {formMode === "edit" ? (
                <div className="flex items-center gap-2">
                  <Checkbox
                    id="attorney-active"
                    checked={formValues.is_active}
                    onCheckedChange={(checked) =>
                      setFormValues((v) => ({
                        ...v,
                        is_active: checked === true,
                      }))
                    }
                    disabled={saving}
                  />
                  <Label htmlFor="attorney-active" className="cursor-pointer font-normal">
                    Active account
                  </Label>
                </div>
              ) : null}
            </div>

            <div className="flex flex-wrap gap-2">
              <Button type="button" disabled={saving} onClick={() => void handleSave()}>
                {saving ? (
                  <>
                    <Loader2 className="animate-spin" aria-hidden />
                    Saving…
                  </>
                ) : formMode === "create" ? (
                  "Create attorney"
                ) : (
                  "Save changes"
                )}
              </Button>
              <Button type="button" variant="outline" disabled={saving} onClick={closeForm}>
                Cancel
              </Button>
            </div>

            {formError ? (
              <Alert variant="destructive">
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <div className="surface-card overflow-hidden rounded-xl">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Login email</TableHead>
              <TableHead>Work email</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Default</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <LoadingRows />
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">
                  No attorneys found. Add one to get started.
                </TableCell>
              </TableRow>
            ) : (
              items.map((account) => {
                const isEditing = formMode === "edit" && editingId === account.id;

                return (
                  <TableRow
                    key={account.id}
                    className={cn(
                      "cursor-pointer transition-colors hover:bg-accent/50",
                      isEditing && "bg-accent/40",
                      formMode !== null && !isEditing && formMode === "edit" && "opacity-60",
                    )}
                    tabIndex={0}
                    onClick={() => {
                      if (formMode === "create") {
                        return;
                      }
                      openEdit(account);
                    }}
                    onKeyDown={(event) => {
                      if (
                        formMode !== "create" &&
                        (event.key === "Enter" || event.key === " ")
                      ) {
                        event.preventDefault();
                        openEdit(account);
                      }
                    }}
                  >
                    <TableCell className="font-medium">
                      {account.first_name} {account.last_name}
                    </TableCell>
                    <TableCell>{account.email}</TableCell>
                    <TableCell>{account.work_email ?? "—"}</TableCell>
                    <TableCell>
                      {account.is_active ? (
                        <Badge variant="success">Active</Badge>
                      ) : (
                        <Badge variant="muted">Inactive</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {account.is_default_assignee ? (
                        <Badge variant="warning">Default</Badge>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      {total > 0 ? (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-muted-foreground">
            Showing {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of{" "}
            {total}
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1 || loading}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </Button>
            <span className="min-w-16 text-center text-sm text-muted-foreground">
              Page {page} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages || loading}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      ) : null}
    </FadeIn>
  );
}
