// src/app/services/auth.service.ts
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { tap } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  // Existing login state management
  private loggedIn = new BehaviorSubject<boolean>(false);
  isLoggedIn$ = this.loggedIn.asObservable();

  private baseUrl = 'http://localhost:5000'; // Backend URL

  constructor(private http: HttpClient) {
    // Optionally check localStorage to persist login state across reloads
    const token = localStorage.getItem('access_token');
    if (token) {
      this.loggedIn.next(true);
    }
  }

  // Called when login is successful
  login() {
    this.loggedIn.next(true);
    console.log('User logged in');
  }

  logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_info');
    this.loggedIn.next(false);
    console.log('User logged out');
  }

  // API call to register a new user
  register(data: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/user_register`, data);
  }

  // API call to authenticate the user
  loginRequest(data: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/user_login`, data).pipe(
      tap((res: any) => {
        if (res.access_token) {
          localStorage.setItem('access_token', res.access_token);
          localStorage.setItem('user_info', JSON.stringify(res.info));
          this.login(); // update the BehaviorSubject state
        }
      })
    );
  }
}
