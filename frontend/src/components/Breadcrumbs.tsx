import type { LucideIcon } from "lucide-react";
import { ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";

type BreadcrumbItem = {
  label: string;
  to?: string;
  icon?: LucideIcon;
};

type BreadcrumbsProps = {
  items: BreadcrumbItem[];
};

export function Breadcrumbs({ items }: BreadcrumbsProps) {
  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      {items.map((item, index) => {
        const Icon = item.icon;
        const isLast = index === items.length - 1;
        return (
          <span key={`${item.label}-${index}`} className={`breadcrumbs-item${isLast ? " active" : ""}`}>
            {Icon ? <Icon size={14} /> : null}
            {item.to && !isLast ? <Link to={item.to}>{item.label}</Link> : <span>{item.label}</span>}
            {!isLast ? <ChevronRight size={14} className="breadcrumbs-separator" /> : null}
          </span>
        );
      })}
    </nav>
  );
}
