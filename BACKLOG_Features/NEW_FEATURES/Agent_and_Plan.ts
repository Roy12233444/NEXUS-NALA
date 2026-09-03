// --- Component ---
"use client";

import {
    memo,
    useCallback,
    useEffect,
    useRef,
    useState,
    type ComponentType,
    type ReactNode,
} from "react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { IconCheck, IconChevronDown } from "@tabler/icons-react";

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

export type ModeOption = {
    id: string;
    label: string;
    icon?: ComponentType<{ className?: string }>;
    description?: string;
};

export type ModeSelectorProps = {
    modes: ModeOption[];
    value?: string;
    defaultValue?: string;
    onChange?: (modeId: string) => void;
    className?: string;
};

function Popover({
    trigger,
    children,
    open,
    onOpenChange,
}: {
    trigger: ReactNode;
    children: ReactNode;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}) {
    const wrapRef = useRef<HTMLSpanElement | null>(null);

    useEffect(() => {
        if (!open) return;
        function onDocClick(e: MouseEvent) {
            if (!wrapRef.current) return;
            if (!wrapRef.current.contains(e.target as Node)) onOpenChange(false);
        }
        function onKey(e: KeyboardEvent) {
            if (e.key === "Escape") onOpenChange(false);
        }
        document.addEventListener("mousedown", onDocClick);
        document.addEventListener("keydown", onKey);
        return () => {
            document.removeEventListener("mousedown", onDocClick);
            document.removeEventListener("keydown", onKey);
        };
    }, [open, onOpenChange]);

    return (
        <span ref= { wrapRef } className = "relative inline-flex" >
            <span onClick={ () => onOpenChange(!open) } className = "inline-flex" >
                { trigger }
                </span>
    {
        open && (
            <div
          role="dialog"
        className = "absolute bottom-full left-0 z-50 mb-1.5 min-w-[180px] rounded-[10px] border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-1 shadow-lg outline-none text-neutral-900 dark:text-neutral-100"
            >
            { children }
            </div>
      )
    }
    </span>
  );
}

export const ModeSelector = memo(function ModeSelector({
    modes,
    value,
    defaultValue,
    onChange,
    className,
}: ModeSelectorProps) {
    const isControlled = value !== undefined;
    const [internalValue, setInternalValue] = useState(defaultValue);
    const activeId = isControlled ? value : internalValue;
    const activeMode = modes.find((m) => m.id === activeId) ?? modes[0];
    const [open, setOpen] = useState(false);

    const handleSelect = useCallback(
        (id: string) => {
            if (!isControlled) setInternalValue(id);
            onChange?.(id);
            setOpen(false);
        },
        [isControlled, onChange],
    );

    if (modes.length === 0) return null;
    const ActiveIcon = activeMode?.icon;
    const hasMultiple = modes.length > 1;

    const trigger = (
        <button
      type= "button"
    className = {
        cn(
        "inline-flex h-7 items-center gap-1.5 rounded-[6px] px-2 text-[12px] leading-4 text-neutral-500 dark:text-neutral-400 transition-colors hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer",
        !hasMultiple && "pointer-events-none",
        className,
      )}
aria - label="Select mode"
    >
    { ActiveIcon && <ActiveIcon className="size-3.5 shrink-0" />}
<span className="font-medium" > { activeMode?.label } </span>
{
    hasMultiple && (
        <IconChevronDown className="size-3 text-neutral-500 dark:text-neutral-400" />
      )
}
</button>
  );

if (!hasMultiple) return trigger;

return (
    <Popover open= { open } onOpenChange = { setOpen } trigger = { trigger } >
    {
        modes.map((mode) => {
            const isActive = mode.id === activeMode?.id;
            const Icon = mode.icon;
            return (
                <button
            key= { mode.id }
            type = "button"
            onClick = {() => handleSelect(mode.id)
        }
            className = {
                cn(
              "flex w-full items-start gap-2 rounded-[6px] px-2 py-1.5 text-left text-[12px] leading-4 text-neutral-900 dark:text-neutral-100 transition-colors hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer",
                    isActive && "bg-neutral-100 dark:bg-neutral-800",
        )
    }
        >
        { Icon && <Icon className="mt-0.5 size-3.5 shrink-0" />}
<span className="flex-1 min-w-0" >
    <span className="block truncate font-medium" > { mode.label } </span>
{
    mode.description && (
        <span className="block truncate text-neutral-500 dark:text-neutral-400" >
            { mode.description }
            </span>
              )
}
</span>
{
    isActive && (
        <IconCheck className="mt-0.5 size-3.5 shrink-0 text-neutral-700 dark:text-neutral-300" />
            )
}
</button>
        );
      })}
</Popover>
  );
});


// --- Demo ---
import { ModeSelector, type ModeOption } from "@/components/ui/mode-selector";
import { IconInfinity, IconListCheck } from "@tabler/icons-react";

const modes: ModeOption[] = [
    {
        id: "agent",
        label: "Agent",
        icon: IconInfinity,
        description: "Plan and execute tasks autonomously",
    },
    {
        id: "plan",
        label: "Plan",
        icon: IconListCheck,
        description: "Outline steps before acting",
    },
];

export default function Demo() {
    return (
        <div className= "flex items-center justify-center w-full min-h-screen bg-background p-8 overflow-hidden" >
        <div className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-950 p-12 w-full max-w-md flex items-center justify-center" >
            <ModeSelector modes={ modes } defaultValue = "agent" />
                </div>
                </div>
  );
}
