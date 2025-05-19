import React from "react";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";
import { useCurrentUser, firebaseAuth } from "app";
import { Toaster } from "sonner";

export default function App() {
  const navigate = useNavigate();
  const { user, loading } = useCurrentUser();

  return (
    <div className="flex flex-col min-h-screen bg-background">
      <Toaster position="top-right" />
      {/* Header */}
      <header className="py-4 px-6 border-b">
        <div className="container mx-auto flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <div className="h-8 w-8 rounded-md bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-semibold">EP</span>
            </div>
            <h1 className="text-xl font-semibold">EndoTrack Pro</h1>
          </div>
          <div className="flex items-center space-x-4">
            {loading ? (
              <div className="w-24 h-10 bg-muted animate-pulse rounded-md"></div>
            ) : user ? (
              <div className="flex items-center space-x-4">
                <Button
                  variant="outline"
                  onClick={() => React.startTransition(() => navigate("/dashboard"))}
                >
                  Dashboard
                </Button>
                <Button 
                  variant="outline" 
                  onClick={() => firebaseAuth.signOut()}
                >
                  Log Out
                </Button>
              </div>
            ) : (
              <div className="flex items-center space-x-4">
                <Button
                  variant="outline"
                  onClick={() => React.startTransition(() => navigate("/login"))}
                >
                  Log In
                </Button>
                <Button
                  onClick={() => React.startTransition(() => navigate("/login"))}
                >
                  Get Started
                </Button>
              </div>
            )}
          </div>
        </div>
      </header>
      
      <main className="flex-1">
        {/* Hero Section */}
        <section className="py-16 md:py-24 px-4">
          <div className="container mx-auto max-w-6xl">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <div>
                <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
                  Precision Tracking for Endoscope Repairs
                </h1>
                <p className="text-lg text-muted-foreground mb-8">
                  EndoTrack Pro helps medical equipment administrators monitor endoscope repair cycles, track replacement chains, and manage orphaned serials with clinical precision.
                </p>
                <div className="flex flex-col sm:flex-row gap-4">
                  <Button
                    size="lg"
                    onClick={() => React.startTransition(() => navigate("/login"))}
                  >
                    Start Tracking Today
                  </Button>
                  <Button
                    variant="outline"
                    size="lg"
                    onClick={() => React.startTransition(() => navigate("/login"))}
                  >
                    Schedule Demo
                  </Button>
                </div>
              </div>
              <div className="relative">
                <div className="aspect-video bg-muted rounded-lg shadow-lg overflow-hidden">
                  {/* This would be an actual image in production */}
                  <div className="absolute inset-0 flex items-center justify-center p-8">
                    <div className="w-full h-full bg-secondary/70 rounded-md flex items-center justify-center">
                      <div className="text-center">
                        <div className="mb-4 flex justify-center">
                          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-primary">
                            <path d="M21 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v3" />
                            <path d="M21 16v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-3" />
                            <path d="M4 12H2" />
                            <path d="M10 12H8" />
                            <path d="M16 12h-2" />
                            <path d="M22 12h-2" />
                          </svg>
                        </div>
                        <p className="text-sm font-medium">Dashboard Preview</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
        
        {/* Features Section */}
        <section className="py-16 px-4 bg-muted/50">
          <div className="container mx-auto max-w-6xl">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold mb-4">Professional Equipment Management</h2>
              <p className="text-muted-foreground max-w-2xl mx-auto">
                Purpose-built for medical equipment administrators who need to maintain precise tracking of endoscope repair cycles.
              </p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {/* Feature 1 */}
              <div className="bg-card rounded-lg p-6 shadow-sm">
                <div className="mb-4 h-12 w-12 rounded-md bg-primary/10 flex items-center justify-center">
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary">
                    <path d="M18 21a8 8 0 0 0-16 0" />
                    <circle cx="10" cy="8" r="5" />
                    <path d="M22 20c0-3.37-2-6.5-4-8a5 5 0 0 0-.45-8.3" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold mb-2">Cohort Tracking</h3>
                <p className="text-muted-foreground">
                  Group and monitor endoscopes by customer service agreement cohorts to keep track of replacement limits and service history.
                </p>
              </div>
              
              {/* Feature 2 */}
              <div className="bg-card rounded-lg p-6 shadow-sm">
                <div className="mb-4 h-12 w-12 rounded-md bg-primary/10 flex items-center justify-center">
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary">
                    <path d="M9 2v6" />
                    <path d="M15 2v6" />
                    <path d="M12 8v6" />
                    <path d="M6 16a6 6 0 0 0 12 0" />
                    <path d="M9 22v-4" />
                    <path d="M15 22v-4" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold mb-2">Replacement Chain Analysis</h3>
                <p className="text-muted-foreground">
                  Visualize and analyze complete replacement chains to understand the full history of each endoscope in your inventory.
                </p>
              </div>
              
              {/* Feature 3 */}
              <div className="bg-card rounded-lg p-6 shadow-sm">
                <div className="mb-4 h-12 w-12 rounded-md bg-primary/10 flex items-center justify-center">
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary">
                    <path d="M22 12c0 6-3.37 10-7.5 10S7 18 7 12" />
                    <path d="M2 12c0-6 3.37-10 7.5-10S17 6 17 12" />
                    <path d="M7 12h10" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold mb-2">Orphan Management</h3>
                <p className="text-muted-foreground">
                  Identify and assign orphaned serials to appropriate cohorts, ensuring complete tracking coverage across your endoscope inventory.
                </p>
              </div>
            </div>
          </div>
        </section>
        
        {/* Benefits Section */}
        <section className="py-16 px-4">
          <div className="container mx-auto max-w-6xl">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <div className="order-2 md:order-1">
                <div className="bg-muted rounded-lg p-8 relative overflow-hidden">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-card rounded-md p-4 shadow-sm">
                      <div className="font-mono text-sm mb-1 text-muted-foreground">SO-00042</div>
                      <div className="font-medium">Cohort Status</div>
                      <div className="mt-2 text-sm"><span className="font-medium text-green-600">12</span> in field</div>
                    </div>
                    <div className="bg-card rounded-md p-4 shadow-sm">
                      <div className="font-mono text-sm mb-1 text-muted-foreground">P313N00</div>
                      <div className="font-medium">SKU Analysis</div>
                      <div className="mt-2 text-sm"><span className="font-medium text-amber-600">4/10</span> replacements</div>
                    </div>
                    <div className="bg-card rounded-md p-4 shadow-sm">
                      <div className="font-mono text-sm mb-1 text-muted-foreground">SN-87654</div>
                      <div className="font-medium">Serial Tracking</div>
                      <div className="mt-2 text-sm"><span className="inline-block w-2 h-2 rounded-full bg-green-500 mr-1"></span> Active</div>
                    </div>
                    <div className="bg-card rounded-md p-4 shadow-sm">
                      <div className="font-mono text-sm mb-1 text-muted-foreground">Orphans</div>
                      <div className="font-medium">Assignment</div>
                      <div className="mt-2 text-sm"><span className="font-medium text-blue-600">26</span> identified</div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="order-1 md:order-2">
                <h2 className="text-3xl font-bold mb-6">Make Data-Driven Decisions</h2>
                <ul className="space-y-4">
                  <li className="flex">
                    <div className="mr-4 h-6 w-6 rounded-full bg-primary/10 flex-shrink-0 flex items-center justify-center">
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary">
                        <path d="M20 6 9 17l-5-5" />
                      </svg>
                    </div>
                    <p className="text-muted-foreground">
                      <span className="font-medium text-foreground">Reduce administrative overhead</span> with automated tracking of all endoscope serials and their replacement history.
                    </p>
                  </li>
                  <li className="flex">
                    <div className="mr-4 h-6 w-6 rounded-full bg-primary/10 flex-shrink-0 flex items-center justify-center">
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary">
                        <path d="M20 6 9 17l-5-5" />
                      </svg>
                    </div>
                    <p className="text-muted-foreground">
                      <span className="font-medium text-foreground">Maintain accurate CSA compliance</span> by ensuring all replacement chains are properly documented and validated.
                    </p>
                  </li>
                  <li className="flex">
                    <div className="mr-4 h-6 w-6 rounded-full bg-primary/10 flex-shrink-0 flex items-center justify-center">
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary">
                        <path d="M20 6 9 17l-5-5" />
                      </svg>
                    </div>
                    <p className="text-muted-foreground">
                      <span className="font-medium text-foreground">Identify coverage gaps</span> by finding orphaned serials and properly assigning them to their appropriate cohorts.
                    </p>
                  </li>
                  <li className="flex">
                    <div className="mr-4 h-6 w-6 rounded-full bg-primary/10 flex-shrink-0 flex items-center justify-center">
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary">
                        <path d="M20 6 9 17l-5-5" />
                      </svg>
                    </div>
                    <p className="text-muted-foreground">
                      <span className="font-medium text-foreground">Generate comprehensive reports</span> for management, audits, and future resource planning with just a few clicks.
                    </p>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </section>
        
        {/* CTA Section */}
        <section className="py-16 px-4 bg-primary text-primary-foreground">
          <div className="container mx-auto max-w-4xl text-center">
            <h2 className="text-3xl font-bold mb-4">Ready to Streamline Your Endoscope Management?</h2>
            <p className="text-primary-foreground/80 mb-8 max-w-2xl mx-auto">
              Join medical equipment administrators who are using EndoTrack Pro to maintain precision tracking of their endoscope inventory and repair cycles.
            </p>
            <Button
              size="lg"
              variant="secondary"
              onClick={() => React.startTransition(() => navigate("/login"))}
              className="font-medium"
            >
              Get Started Today
            </Button>
          </div>
        </section>
      </main>
      
      {/* Footer */}
      <footer className="py-8 px-4 border-t">
        <div className="container mx-auto">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center space-x-2 mb-4 md:mb-0">
              <div className="h-6 w-6 rounded-md bg-primary flex items-center justify-center">
                <span className="text-primary-foreground text-xs font-semibold">EP</span>
              </div>
              <span className="text-sm font-medium">EndoTrack Pro</span>
            </div>
            <div className="text-sm text-muted-foreground">
              &copy; {new Date().getFullYear()} EndoTrack Pro. All rights reserved.
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
