import { Routes } from '@angular/router';
import { HomeComponent } from './home/home.component';
import { AboutComponent } from './pages/about/about.component'; // Import About
import { ContactComponent } from './pages/contact/contact.component'; // Import Contact


export const routes: Routes = [
    { path: '', component: HomeComponent },
    { path: 'about', component: AboutComponent },
    { path: 'contact', component: ContactComponent },
    // { path: 'auth', component: AuthComponent }, // <-- DELETE THIS LINE
    { path: '**', redirectTo: '' }
];
