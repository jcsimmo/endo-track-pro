import type { ReactNode } from "react";
import { Toaster } from "sonner";

interface Props {
  children: ReactNode;
}

/**
 * A provider wrapping the whole app.
 *
 * You can add multiple providers here by nesting them,
 * and they will all be applied to the app.
 * 
 * The following are already initialized and available in the app:
 * - Firebase Auth: Import { firebaseAuth, useCurrentUser } from "app";
 * - Firestore: Import { firestore } from "app";
 */
export const AppProvider = ({ children }: Props) => {
  return (
    <>
      <Toaster position="top-right" />
      {children}
    </>
  );
};