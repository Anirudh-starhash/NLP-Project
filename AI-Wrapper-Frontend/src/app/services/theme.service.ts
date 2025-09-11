import { Injectable, RendererFactory2, Renderer2 } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

type Theme = 'light' | 'dark';

@Injectable({
  providedIn: 'root'
})
export class ThemeService {
  private renderer: Renderer2;
  private _theme$ = new BehaviorSubject<Theme>('light');
  public theme$ = this._theme$.asObservable();

  constructor(rendererFactory: RendererFactory2) {
    this.renderer = rendererFactory.createRenderer(null, null);
  }

  // Called once from AppComponent to set the initial theme
  initializeTheme() {
    const savedTheme = localStorage.getItem('app-theme') as Theme;
    if (savedTheme) {
      this.setTheme(savedTheme);
    } else {
      // Fallback to user's system preference
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
      this.setTheme(prefersDark.matches ? 'dark' : 'light');
    }
  }

  setTheme(theme: Theme) {
    // 1. Save the new theme to local storage
    localStorage.setItem('app-theme', theme);

    // 2. Update the BehaviorSubject to notify subscribers
    this._theme$.next(theme);

    // 3. Update the class on the <body> element
    if (theme === 'dark') {
      this.renderer.addClass(document.body, 'dark-theme');
    } else {
      this.renderer.removeClass(document.body, 'dark-theme');
    }
  }

  toggleTheme() {
    const currentTheme = this._theme$.value;
    this.setTheme(currentTheme === 'light' ? 'dark' : 'light');
  }
}
