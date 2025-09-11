import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  // Use a BehaviorSubject to hold the current login state.
  // It's initialized to 'false' (logged out).
  private loggedIn = new BehaviorSubject<boolean>(false);

  // Expose the login state as an observable. Components can subscribe to this.
  isLoggedIn$ = this.loggedIn.asObservable();

  constructor() { }

  login() {
    // In a real app, you'd perform authentication here.
    // For now, we'll just set the state to true.
    this.loggedIn.next(true);
    console.log('User logged in');
  }

  logout() {
    this.loggedIn.next(false);
    console.log('User logged out');
  }
}
