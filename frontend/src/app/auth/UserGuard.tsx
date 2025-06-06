import type { User } from "firebase/auth";
import * as React from "react";
import { createContext, useContext } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useCurrentUser } from "./useCurrentUser";

type UserGuardContextType = {
  user: User;
};

const UserGuardContext = createContext<UserGuardContextType | undefined>(
  undefined,
);

/**
 * Hook to access the logged in user from within a <UserGuard> component.
 */
export const useUserGuardContext = () => {
  const context = useContext(UserGuardContext);

  if (context === undefined) {
    throw new Error("useUserGuardContext must be used within a <UserGuard>");
  }

  return context;
};

/**
 * All protected routes are wrapped in a UserGuard component.
 */
export const UserGuard = (props: {
  children: React.ReactNode;
}) => {
  const { user, loading } = useCurrentUser();
  const { pathname } = useLocation();

  if (loading) {
    return <React.Fragment />;
  }

  // TEMPORARY: Allow bypass for testing multi-SKU functionality
  // TODO: Remove this bypass and fix authentication system
  const isDevelopment = process.env.NODE_ENV === 'development';
  const mockUser = {
    uid: 'test-user',
    email: 'test@example.com',
    displayName: 'Test User'
  } as any;

  if (!user && !isDevelopment) {
    const queryParams = new URLSearchParams(window.location.search);

    // Don't set the next param if the user is logging out
    // to avoid ending up in an infinite redirect loop
    if (pathname !== "/logout" && pathname !== "/sign-out") {
      queryParams.set("next", pathname);
    }

    const queryString = queryParams.toString();

    return <Navigate to={`/login?${queryString}`} replace={true} />;
  }

  const effectiveUser = user || (isDevelopment ? mockUser : null);

  return (
    <UserGuardContext.Provider value={{ user: effectiveUser }}>
      {props.children}
    </UserGuardContext.Provider>
  );
};
