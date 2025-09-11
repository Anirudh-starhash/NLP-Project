import { Routes } from '@angular/router';
import { HomeComponent } from './home/home.component';
import { AboutComponent } from './pages/about/about.component';
import { ContactComponent } from './pages/contact/contact.component';
import { DashboardComponent } from './pages/dashboard/dashboard.component'; // Import Dashboard
import { ProfileComponent } from './pages/profile/profile.component';     // Import Profile
import { authGuard } from './auth/auth.guard';                         // Import the Guard

export const routes: Routes = [
  { path: '', component: HomeComponent },
  { path: 'about', component: AboutComponent },
  { path: 'contact', component: ContactComponent },

  // --- PROTECTED ROUTES ---
  {
    path: 'dashboard',
    component: DashboardComponent,
    canActivate: [authGuard] // Protect this route
  },
  {
    path: 'profile',
    component: ProfileComponent,
    canActivate: [authGuard] // Protect this route
  },

  { path: '**', redirectTo: '' }
];
