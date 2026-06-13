"use client"

import type * as React from "react"
import {
  BarChart3Icon,
  BotIcon,
  DatabaseIcon,
  HeartPulseIcon,
  LogOutIcon,
  MegaphoneIcon,
  UploadCloudIcon,
} from "lucide-react"

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"

const navItems = [
  { title: "Overview", icon: BarChart3Icon },
  { title: "Assistant", icon: BotIcon },
  { title: "Customer health", icon: HeartPulseIcon },
  { title: "Campaigns", icon: MegaphoneIcon },
  { title: "Uploads", icon: UploadCloudIcon },
]

type AppSidebarProps = React.ComponentProps<typeof Sidebar> & {
  email?: string | null
  onLogout?: () => void
}

export function AppSidebar({ email, onLogout, ...props }: AppSidebarProps) {
  const initials = (email || "FinChat")
    .split("@")[0]
    .slice(0, 2)
    .toUpperCase()

  return (
    <Sidebar collapsible="offcanvas" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton className="h-12 gap-3">
              <div className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <DatabaseIcon className="size-5" />
              </div>
              <div className="grid text-left text-sm leading-tight">
                <span className="font-semibold">FinChat Analytics</span>
                <span className="text-xs text-muted-foreground">Retention command center</span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Workspace</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <a href={`#${item.title.toLowerCase().replaceAll(" ", "-")}`}>
                      <item.icon />
                      <span>{item.title}</span>
                    </a>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <div className="flex items-center gap-3 rounded-lg border bg-card p-3">
          <Avatar className="size-9">
            <AvatarFallback>{initials}</AvatarFallback>
          </Avatar>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{email || "Google user"}</p>
            <p className="text-xs text-muted-foreground">BANK001</p>
          </div>
          <Button variant="ghost" size="icon" onClick={onLogout} aria-label="Sign out">
            <LogOutIcon className="size-4" />
          </Button>
        </div>
      </SidebarFooter>
    </Sidebar>
  )
}
