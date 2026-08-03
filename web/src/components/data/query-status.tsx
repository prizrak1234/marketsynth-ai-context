"use client";



import type { UseQueryResult } from "@tanstack/react-query";

import { ApiError } from "@/lib/api/errors";

import { EmptyState } from "@/components/data/empty-state";

import { ErrorPanel } from "@/components/data/error-panel";

import { LoadingSkeleton } from "@/components/data/loading-skeleton";



type QueryStatusProps<T> = {

  query: UseQueryResult<T>;

  empty?: boolean;

  emptyTitle?: string;

  emptyDescription?: string;

  emptyAction?: React.ReactNode;

  loadingVariant?: "text" | "card" | "table";

  loadingLines?: number;

  children: (data: T) => React.ReactNode;

};



function errorMessage(error: unknown): string {

  if (error instanceof ApiError) {

    return error.message;

  }

  if (error instanceof Error) {

    return error.message;

  }

  return "Request failed";

}



export function QueryStatus<T>({

  query,

  empty = false,

  emptyTitle = "Nothing here yet",

  emptyDescription,

  emptyAction,

  loadingVariant = "text",

  loadingLines = 3,

  children,

}: QueryStatusProps<T>) {

  if (query.isPending) {

    return (

      <LoadingSkeleton

        variant={loadingVariant}

        lines={loadingLines}

      />

    );

  }



  if (query.isError) {

    return <ErrorPanel message={errorMessage(query.error)} />;

  }



  if (empty) {

    return (

      <EmptyState

        title={emptyTitle}

        description={emptyDescription}

        action={emptyAction}

      />

    );

  }



  return <>{children(query.data as T)}</>;

}


