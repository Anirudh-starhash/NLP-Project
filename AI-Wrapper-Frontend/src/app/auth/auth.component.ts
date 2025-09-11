import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { AuthService } from '../services/auth.service';
import { Router } from '@angular/router';
import { LoginComponent } from "../login/login.component";
import { RegisterComponent } from '../register/register.component';

@Component({
  selector: 'app-auth',
  standalone: true,
  imports: [CommonModule, LoginComponent, RegisterComponent],
  templateUrl: './auth.component.html',
  styleUrls: ['./auth.component.css']
})
export class AuthComponent implements OnInit {
  isLoginView = true;

  constructor(
    private authService: AuthService,
    private router: Router,
    // This allows us to control the dialog itself (e.g., close it)
    public dialogRef: MatDialogRef<AuthComponent>,
    // This injects the data we pass when opening the dialog
    @Inject(MAT_DIALOG_DATA) public data: { initialView: 'login' | 'register' }
  ) {}

  ngOnInit(): void {
    // Set the initial view based on the data passed to the dialog
    this.isLoginView = this.data.initialView === 'login';
  }

  // A single method for both login and register submission
  onSubmit() {
    console.log('Form submitted');
    this.authService.login();
    this.router.navigate(['/dashboard']);
    this.dialogRef.close(); // Close the dialog on successful submission
  }

  toggleAuthView(){
    this.isLoginView = !this.isLoginView;
  }

}
