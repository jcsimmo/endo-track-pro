import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useNavigate } from "react-router-dom";
import { firebaseAuth } from "app";
import { signInWithEmailAndPassword, createUserWithEmailAndPassword, GoogleAuthProvider, signInWithPopup } from "firebase/auth";
import { toast } from "sonner";

export default function Login() {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  
  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      toast.error("Please enter both email and password");
      return;
    }
    
    setIsLoading(true);
    try {
      if (isSignUp) {
        await createUserWithEmailAndPassword(firebaseAuth, email, password);
        toast.success("Account created successfully!");
        navigate("/dashboard");
      } else {
        await signInWithEmailAndPassword(firebaseAuth, email, password);
        toast.success("Signed in successfully!");
        navigate("/dashboard");
      }
    } catch (error: any) {
      console.error("Authentication error:", error);
      toast.error(error.message || "Authentication failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleGoogleSignIn = async () => {
    setIsLoading(true);
    try {
      await signInWithPopup(firebaseAuth, new GoogleAuthProvider());
      toast.success("Signed in with Google successfully!");
      navigate("/dashboard");
    } catch (error: any) {
      console.error("Google sign-in error:", error);
      toast.error(error.message || "Google sign-in failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-background">
      <div className="flex-1 hidden md:block bg-muted/60">
        <div className="h-full flex items-center justify-center p-8">
          <div className="max-w-md">
            <div className="flex items-center space-x-2 mb-6">
              <div className="h-8 w-8 rounded-md bg-primary flex items-center justify-center">
                <span className="text-primary-foreground font-semibold">EP</span>
              </div>
              <h1 className="text-xl font-semibold">EndoTrack Pro</h1>
            </div>
            <h2 className="text-3xl font-bold text-foreground mb-4">Precision Tracking for Medical Equipment</h2>
            <p className="text-muted-foreground">
              EndoTrack Pro helps medical equipment administrators monitor endoscope repair cycles with clinical precision.
            </p>
            <div className="mt-8 space-y-4">
              <div className="bg-card rounded-lg p-4 shadow-sm">
                <div className="flex items-start">
                  <div className="mr-4 h-6 w-6 rounded-full bg-primary/10 flex-shrink-0 flex items-center justify-center">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary">
                      <path d="M20 6 9 17l-5-5" />
                    </svg>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    <span className="font-medium text-foreground">Track complex replacement chains</span> with our intuitive visualizations and cohort management system.
                  </p>
                </div>
              </div>
              <div className="bg-card rounded-lg p-4 shadow-sm">
                <div className="flex items-start">
                  <div className="mr-4 h-6 w-6 rounded-full bg-primary/10 flex-shrink-0 flex items-center justify-center">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary">
                      <path d="M20 6 9 17l-5-5" />
                    </svg>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    <span className="font-medium text-foreground">Manage orphaned serials</span> and identify coverage gaps in your endoscope inventory tracking.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-sm space-y-8">
          <div className="text-center">
            <h2 className="text-2xl font-bold tracking-tight">Welcome back</h2>
            <p className="text-sm text-muted-foreground mt-2">
              Sign in to continue to EndoTrack Pro
            </p>
          </div>
          <form onSubmit={handleAuth} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                Email
              </label>
              <Input
                id="email"
                type="email"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isLoading}
                required
              />
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label htmlFor="password" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                  Password
                </label>
                {!isSignUp && (
                  <button 
                    type="button"
                    className="text-sm font-medium text-primary hover:underline"
                    onClick={() => toast.info("Password reset functionality will be added soon.")}
                  >
                    Forgot password?
                  </button>
                )}
              </div>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isLoading}
                required
              />
            </div>
            <Button className="w-full" type="submit" disabled={isLoading}>
              {isLoading ? "Processing..." : isSignUp ? "Sign Up" : "Sign In"}
            </Button>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-background px-2 text-muted-foreground">Or continue with</span>
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t"></span>
              </div>
            </div>
            <Button 
              type="button" 
              variant="outline" 
              className="w-full" 
              onClick={handleGoogleSignIn}
              disabled={isLoading}
            >
              <svg className="mr-2 h-4 w-4" aria-hidden="true" focusable="false" data-prefix="fab" data-icon="google" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 488 512">
                <path fill="currentColor" d="M488 261.8C488 403.3 391.1 504 248 504 110.8 504 0 393.2 0 256S110.8 8 248 8c66.8 0 123 24.5 166.3 64.9l-67.5 64.9C258.5 52.6 94.3 116.6 94.3 256c0 86.5 69.1 156.6 153.7 156.6 98.2 0 135-70.4 140.8-106.9H248v-85.3h236.1c2.3 12.7 3.9 24.9 3.9 41.4z"></path>
              </svg>
              Sign in with Google
            </Button>
            <div className="text-center text-sm">
              <span className="text-muted-foreground">{isSignUp ? "Already have an account? " : "Don't have an account? "}</span>
              <button 
                type="button"
                className="font-medium text-primary hover:underline"
                onClick={() => setIsSignUp(!isSignUp)}
              >
                {isSignUp ? "Sign in" : "Sign up"}
              </button>
            </div>
          </form>
          <div className="mt-4 text-center">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => navigate("/")}
              type="button"
            >
              Back to Home
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}