import React, { useState, useEffect, useCallback, useMemo, createContext, useContext } from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

// ============================================================
// Types & Interfaces
// ============================================================
interface UserProfile {
  id: string;
  name: string;
  email: string;
  avatar: string;
  role: 'admin' | 'editor' | 'viewer';
  createdAt: Date;
  lastLogin: Date;
  preferences: UserPreferences;
}

interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  language: string;
  notifications: boolean;
  autoSave: boolean;
  editorFontSize: number;
}

interface TodoItem {
  id: string;
  title: string;
  description: string;
  completed: boolean;
  priority: 'high' | 'medium' | 'low';
  tags: string[];
  dueDate: Date | null;
  assignee: string;
  createdAt: Date;
  updatedAt: Date;
}

interface ApiResponse<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  status: 'idle' | 'loading' | 'success' | 'error';
}

// ============================================================
// Custom Hook: useApi
// ============================================================
function useApi<T>(fetcher: () => Promise<T>): ApiResponse<T> & { refetch: () => void } {
  const [state, setState] = useState<ApiResponse<T>>({
    data: null,
    error: null,
    loading: false,
    status: 'idle',
  });

  const fetchData = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, status: 'loading' }));
    try {
      const result = await fetcher();
      setState({ data: result, error: null, loading: false, status: 'success' });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setState({ data: null, error: message, loading: false, status: 'error' });
    }
  }, [fetcher]);

  useEffect(() => { fetchData(); }, [fetchData]);

  return { ...state, refetch: fetchData };
}

// ============================================================
// Custom Hook: useLocalStorage
// ============================================================
function useLocalStorage<T>(key: string, initialValue: T): [T, (value: T) => void] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? (JSON.parse(item) as T) : initialValue;
    } catch {
      return initialValue;
    }
  });

  const setValue = useCallback(
    (value: T) => {
      setStoredValue(value);
      try {
        window.localStorage.setItem(key, JSON.stringify(value));
      } catch (err) {
        console.error('Failed to save to localStorage:', err);
      }
    },
    [key]
  );

  return [storedValue, setValue];
}

// ============================================================
// Theme Context
// ============================================================
interface ThemeContextType {
  theme: 'light' | 'dark';
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType>({
  theme: 'light',
  toggleTheme: () => {},
});

function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  }, []);
  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

function useTheme(): ThemeContextType {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used within ThemeProvider');
  return context;
}

// ============================================================
// Component: TodoCard
// ============================================================
interface TodoCardProps {
  todo: TodoItem;
  onToggle: (id: string) => void;
  onDelete: (id: string) => void;
  onEdit: (todo: TodoItem) => void;
}

function TodoCard({ todo, onToggle, onDelete, onEdit }: TodoCardProps) {
  const { theme } = useTheme();
  const [expanded, setExpanded] = useState(false);

  const priorityColor = useMemo(() => {
    switch (todo.priority) {
      case 'high': return 'red';
      case 'medium': return 'orange';
      case 'low': return 'green';
      default: return 'gray';
    }
  }, [todo.priority]);

  const formattedDate = useMemo(() => {
    return todo.dueDate
      ? new Date(todo.dueDate).toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
        })
      : 'No due date';
  }, [todo.dueDate]);

  return (
    <div
      className={`todo-card ${todo.completed ? 'completed' : ''} ${theme}`}
      data-testid={`todo-${todo.id}`}
      onClick={() => setExpanded(!expanded)}
      role="article"
      aria-label={`Todo: ${todo.title}`}
    >
      <div className="todo-header">
        <input
          type="checkbox"
          checked={todo.completed}
          onChange={() => onToggle(todo.id)}
          aria-label={`Toggle ${todo.title}`}
          data-testid={`toggle-${todo.id}`}
        />
        <h3 className="todo-title" style={{ textDecoration: todo.completed ? 'line-through' : 'none' }}>
          {todo.title}
        </h3>
        <span className="priority-badge" style={{ backgroundColor: priorityColor }}>
          {todo.priority}
        </span>
      </div>

      {expanded && (
        <div className="todo-details" data-testid={`details-${todo.id}`}>
          <p className="todo-description">{todo.description}</p>
          <div className="todo-meta">
            <span>Due: {formattedDate}</span>
            <span>Assignee: {todo.assignee}</span>
          </div>
          {todo.tags.length > 0 && (
            <div className="todo-tags">
              {todo.tags.map((tag) => (
                <span key={tag} className="tag">{tag}</span>
              ))}
            </div>
          )}
          <div className="todo-actions">
            <button onClick={() => onEdit(todo)} data-testid={`edit-${todo.id}`}>
              Edit
            </button>
            <button onClick={() => onDelete(todo.id)} data-testid={`delete-${todo.id}`}>
              Delete
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================
// Component: UserAvatar
// ============================================================
interface UserAvatarProps {
  user: UserProfile;
  size?: 'small' | 'medium' | 'large';
  showName?: boolean;
}

function UserAvatar({ user, size = 'medium', showName = true }: UserAvatarProps) {
  const sizeMap: Record<string, number> = { small: 32, medium: 48, large: 64 };

  return (
    <div className="user-avatar" data-testid={`avatar-${user.id}`}>
      <img
        src={user.avatar}
        alt={`${user.name}'s avatar`}
        width={sizeMap[size]}
        height={sizeMap[size]}
        style={{ borderRadius: '50%' }}
      />
      {showName && <span className="user-name">{user.name}</span>}
      <span className="user-role">{user.role}</span>
    </div>
  );
}

export {
  UserProfile,
  UserPreferences,
  TodoItem,
  ApiResponse,
  useApi,
  useLocalStorage,
  ThemeProvider,
  useTheme,
  ThemeContext,
  TodoCard,
  TodoCardProps,
  UserAvatar,
  UserAvatarProps,
};
