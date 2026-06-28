"use client";

import { Loader2, Plus, X } from "lucide-react";
import { useCallback, useEffect, useState, startTransition } from "react";

import { useSession } from "@/components/auth/SessionProvider";
import { AdminSubnav } from "@/components/staff/admin/AdminSubnav";
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
import type { AccountRead, AccountUpdate, Paginated, Role } from "@/lib/types";

type StaffAccountsAdminConfig = {
  role: Extract<Role, "attorney" | "intake_coordinator">;
  title: string;
  singular: string;
  plural: string;
  description: string;
  showDefaultAssignee: boolean;
};

export const ATTORNEY_ADMIN_CONFIG: StaffAccountsAdminConfig = {
  role: "attorney",
  title: "Attorneys",
  singular: "attorney",
  plural: "attorneys",
  description: "Click a row to edit an attorney account.",
  showDefaultAssignee: true,
};

export const INTAKE_COORDINATOR_ADMIN_CONFIG: StaffAccountsAdminConfig = {
  role: "intake_coordinator",
  title: "Intake coordinators",
  singular: "intake coordinator",
  plural: "intake coordinators",
  description: "Click a row to edit an intake coordinator account.",
  showDefaultAssignee: false,
};

type StaffFormMode = "create" | "edit";

type StaffFormValues = {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  work_email: string;
  is_default_assignee: boolean;
  is_active: boolean;
};

const EMPTY_CREATE: StaffFormValues = {
  email: "",
  password: "",
  first_name: "",
  last_name: "",
  work_email: "",
  is_default_assignee: false,
  is_active: true,
};

type StaffAccountsAdminPageProps = {
  config: StaffAccountsAdminConfig;
};

function accountToForm(account: AccountRead): StaffFormValues {
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

function LoadingRows({ columns }: { columns: number }) {
  return (
    <>
      {Array.from({ length: 3 }).map((_, index) => (
        <TableRow key={index}>
          {Array.from({ length: columns }).map((__, cellIndex) => (
            <TableCell key={cellIndex}>
              <Skeleton className="h-4 w-full" />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  );
}

export function StaffAccountsAdminPage({ config }: StaffAccountsAdminPageProps) {
  const { user } = useSession();
  const canManage = user.permissions.includes("manage_users");

  const [items, setItems] = useState<AccountRead[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [formMode, setFormMode] = useState<StaffFormMode | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formValues, setFormValues] = useState<StaffFormValues>(EMPTY_CREATE);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const columnCount = config.showDefaultAssignee ? 5 : 4;

  const loadAccounts = useCallback(async () => {
    if (!canManage) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    const result = await staffFetch<Paginated<AccountRead>>(
      `/api/v1/accounts?role=${config.role}&page=${page}&page_size=${pageSize}`,
    );

    setLoading(false);

    if (!result.ok) {
      setError(formatStaffApiError(result.status, result.body));
      return;
    }

    setItems(result.data.items);
    setTotal(result.data.total);
  }, [canManage, config.role, page, pageSize]);

  useEffect(() => {
    startTransition(() => {
      void loadAccounts();
    });
  }, [loadAccounts]);

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
      const createPayload: Record<string, unknown> = {
        email: formValues.email.trim(),
        password: formValues.password,
        role: config.role,
        first_name: formValues.first_name.trim(),
        last_name: formValues.last_name.trim(),
        work_email: formValues.work_email.trim() || null,
      };

      if (config.showDefaultAssignee) {
        createPayload.is_default_assignee = formValues.is_default_assignee;
      }

      const result = await staffFetch<AccountRead>("/api/v1/accounts", {
        method: "POST",
        json: createPayload,
      });

      setSaving(false);

      if (!result.ok) {
        setFormError(formatStaffApiError(result.status, result.body));
        return;
      }

      closeForm();
      void loadAccounts();
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
      is_active: formValues.is_active,
    };

    if (config.showDefaultAssignee) {
      payload.is_default_assignee = formValues.is_default_assignee;
    }

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
    void loadAccounts();
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
  const formIdPrefix = config.role.replace("_", "-");

  return (
    <FadeIn variant="fade" className="space-y-6">
      <AdminSubnav />

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="font-heading text-3xl font-bold tracking-tight">
            {config.title}
          </h1>
          <p className="text-muted-foreground">{config.description}</p>
        </div>
        {!formMode ? (
          <Button type="button" onClick={openCreate}>
            <Plus className="size-4" aria-hidden />
            Add {config.singular}
          </Button>
        ) : null}
      </div>

      {formMode ? (
        <Card>
          <CardHeader className="flex flex-row items-start justify-between gap-4">
            <div>
              <CardTitle>
                {formMode === "create"
                  ? `Add ${config.singular}`
                  : `Edit ${config.singular}`}
              </CardTitle>
              <CardDescription>
                {formMode === "create"
                  ? `Create a new ${config.singular} account. Role cannot be changed later.`
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
                    <Label htmlFor={`${formIdPrefix}-email`}>Login email</Label>
                    <Input
                      id={`${formIdPrefix}-email`}
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
                    <Label htmlFor={`${formIdPrefix}-password`}>Password</Label>
                    <Input
                      id={`${formIdPrefix}-password`}
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
                  <Label htmlFor={`${formIdPrefix}-email-readonly`}>Login email</Label>
                  <Input
                    id={`${formIdPrefix}-email-readonly`}
                    value={formValues.email}
                    disabled
                  />
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor={`${formIdPrefix}-first-name`}>First name</Label>
                <Input
                  id={`${formIdPrefix}-first-name`}
                  value={formValues.first_name}
                  onChange={(e) =>
                    setFormValues((v) => ({ ...v, first_name: e.target.value }))
                  }
                  disabled={saving}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor={`${formIdPrefix}-last-name`}>Last name</Label>
                <Input
                  id={`${formIdPrefix}-last-name`}
                  value={formValues.last_name}
                  onChange={(e) =>
                    setFormValues((v) => ({ ...v, last_name: e.target.value }))
                  }
                  disabled={saving}
                />
              </div>

              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor={`${formIdPrefix}-work-email`}>
                  Work email (optional)
                </Label>
                <Input
                  id={`${formIdPrefix}-work-email`}
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
                  <Label htmlFor={`${formIdPrefix}-new-password`}>
                    New password (optional)
                  </Label>
                  <Input
                    id={`${formIdPrefix}-new-password`}
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
              {config.showDefaultAssignee ? (
                <div className="flex items-center gap-2">
                  <Checkbox
                    id={`${formIdPrefix}-default`}
                    checked={formValues.is_default_assignee}
                    onCheckedChange={(checked) =>
                      setFormValues((v) => ({
                        ...v,
                        is_default_assignee: checked === true,
                      }))
                    }
                    disabled={saving}
                  />
                  <Label
                    htmlFor={`${formIdPrefix}-default`}
                    className="cursor-pointer font-normal"
                  >
                    Default assignee for new leads
                  </Label>
                </div>
              ) : null}

              {formMode === "edit" ? (
                <div className="flex items-center gap-2">
                  <Checkbox
                    id={`${formIdPrefix}-active`}
                    checked={formValues.is_active}
                    onCheckedChange={(checked) =>
                      setFormValues((v) => ({
                        ...v,
                        is_active: checked === true,
                      }))
                    }
                    disabled={saving}
                  />
                  <Label
                    htmlFor={`${formIdPrefix}-active`}
                    className="cursor-pointer font-normal"
                  >
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
                  `Create ${config.singular}`
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
              {config.showDefaultAssignee ? (
                <TableHead>Default</TableHead>
              ) : null}
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <LoadingRows columns={columnCount} />
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={columnCount}
                  className="py-8 text-center text-muted-foreground"
                >
                  No {config.plural} found. Add one to get started.
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
                    {config.showDefaultAssignee ? (
                      <TableCell>
                        {account.is_default_assignee ? (
                          <Badge variant="warning">Default</Badge>
                        ) : (
                          "—"
                        )}
                      </TableCell>
                    ) : null}
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
