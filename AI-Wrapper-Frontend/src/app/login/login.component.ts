import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [], // No special imports needed for this simple component
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css']
})
export class LoginComponent {
  constructor(private authService: AuthService, private router: Router) { }

  onLogin() {
    console.log('Login form submitted');
    this.authService.login();
    this.router.navigate(['/dashboard']);
  }
}
