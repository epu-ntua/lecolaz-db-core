import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";

export default function AppLayout() {
  return (
    <div className="h-screen overflow-hidden flex bg-background text-foreground">
      <Sidebar />
      <div className="min-w-0 flex-1 flex flex-col overflow-hidden">
        <TopBar />
        <main className="min-w-0 flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
